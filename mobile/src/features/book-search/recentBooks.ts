import { deviceStorage } from "../../lib/platform";
import { RECENT_BOOK_LIMIT } from "../../lib/policy";
import { Book, isBook } from "./api";

const keyFor = (userId: string | null) => `recent_books:${userId ?? "guest"}`;
// 키별 직렬화: 느린 저장/읽기와 연타 삭제가 앞선 변경을 덮지 않는다.
const queues = new Map<string, Promise<unknown>>();
function serial<T>(key: string, work: () => Promise<T>): Promise<T> {
  const next = (queues.get(key) ?? Promise.resolve()).catch(() => undefined).then(work);
  queues.set(key, next);
  void next.finally(() => { if (queues.get(key) === next) queues.delete(key); }).catch(() => undefined);
  return next;
}
async function read(key: string): Promise<Book[]> {
  const raw = await deviceStorage.getItem(key);
  if (raw === null) return [];
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed) || !parsed.every(isBook)) throw new Error("최근 본 도서 저장 내용을 확인하지 못했어요.");
  return parsed.filter((b, i, all) => all.findIndex(x => x.isbn13 === b.isbn13) === i).slice(0, RECENT_BOOK_LIMIT);
}
export const loadRecent = (userId: string | null) => {
  const key = keyFor(userId);
  return serial(key, () => read(key));
};
export function updateRecent(userId: string | null, change: { add: Book } | { remove: string } | { clear: true }): Promise<Book[]> {
  const key = keyFor(userId);
  return serial(key, async () => {
    // 전체 삭제는 손상된 저장 내용도 복구한다.
    const old = "clear" in change ? [] : await read(key);
    const next = "add" in change ? [change.add, ...old.filter(b => b.isbn13 !== change.add.isbn13)].slice(0, RECENT_BOOK_LIMIT) :
      "remove" in change ? old.filter(b => b.isbn13 !== change.remove) : [];
    await deviceStorage.setItem(key, JSON.stringify(next));
    return next;
  });
}
