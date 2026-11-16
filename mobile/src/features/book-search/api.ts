import { BOOK_REQUEST_TIMEOUT_MS } from "../../lib/policy";

export type Book = {
  isbn13: string;
  title: string;
  author: string | null;
  publisher: string | null;
  cover_url: string | null;
  source: "naver" | "data4library" | "manual";
};
export type SearchResult = {
  items: Book[]; next_start: number | null; source: "naver" | "cache";
  fallback_reason: string | null;
};
export type Recommendations = {
  kind: "theme" | "popular"; scope: "library" | "national"; library_id: number | null;
  basis_label: string; theme: { id: number; title: string; description: string | null } | null;
  books: Book[]; fetched_at: string | null; stale: boolean; fallback_reason: string | null;
};
export function isBook(value: unknown): value is Book {
  if (!value || typeof value !== "object") return false;
  const b = value as Record<string, unknown>;
  return typeof b.isbn13 === "string" && /^\d{13}$/.test(b.isbn13) &&
    typeof b.title === "string" && [b.author, b.publisher].every(v => v === null || typeof v === "string") &&
    (b.cover_url === null || (typeof b.cover_url === "string" && b.cover_url.startsWith("https://"))) &&
    ["naver", "data4library", "manual"].includes(String(b.source));
}

// 공개 API: Supabase 세션/토큰이 없는 방문자도 조회한다.
async function request(path: string, signal: AbortSignal): Promise<unknown> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal.addEventListener("abort", cancel, { once: true });
  if (signal.aborted) cancel();
  const timer = setTimeout(cancel, BOOK_REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(`${process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/books${path}`, { signal: controller.signal });
    let body;
    try { body = await res.json(); } catch { throw invalid(); }
    if (!res.ok) throw new Error(body?.error?.message || "정보를 가져오지 못했어요. 다시 시도해 주세요.");
    return body;
  } catch (e) {
    if (controller.signal.aborted) throw new Error("조회 시간이 지났어요. 다시 시도해 주세요.");
    if (e instanceof TypeError) throw new Error("서버에 연결하지 못했어요. 다시 시도해 주세요.");
    throw e;
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", cancel);
  }
}
const invalid = () => new Error("응답을 확인하지 못했어요. 다시 시도해 주세요.");
export async function searchBooks(q: string, start: number, signal: AbortSignal): Promise<SearchResult> {
  const data = await request(`/search?q=${encodeURIComponent(q)}&start=${start}`, signal) as SearchResult;
  if (!data || !Array.isArray(data.items) || !data.items.every(isBook) ||
      !(data.next_start === null || (Number.isInteger(data.next_start) && data.next_start > start && data.next_start <= 1000)) ||
      !["naver", "cache"].includes(data.source)) throw invalid();
  return data;
}
export async function recommendBooks(libraryId: string | undefined, popular: boolean, signal: AbortSignal): Promise<Recommendations> {
  const params = new URLSearchParams({ kind: popular ? "popular" : "auto" });
  if (libraryId) params.set("library_id", libraryId);
  const data = await request(`/recommendations?${params}`, signal) as Recommendations;
  if (!data || !Array.isArray(data.books) || !data.books.every(isBook) ||
      !["theme", "popular"].includes(data.kind) || !["library", "national"].includes(data.scope) ||
      typeof data.basis_label !== "string" || typeof data.stale !== "boolean" ||
      !(data.fetched_at === null || typeof data.fetched_at === "string")) throw invalid();
  return data;
}
export async function fetchBook(isbn13: string, signal: AbortSignal): Promise<Book> {
  const data = await request(`/${encodeURIComponent(isbn13)}`, signal);
  if (!isBook(data) || data.isbn13 !== isbn13) throw invalid();
  return data;
}
