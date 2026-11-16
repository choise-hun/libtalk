import { afterEach, beforeEach, describe, expect, jest, test } from "@jest/globals";
import { fetchBook, recommendBooks, searchBooks } from "../api";
import { BOOK_REQUEST_TIMEOUT_MS } from "../../../lib/policy";

const originalFetch = globalThis.fetch;
const mockFetch = jest.fn<typeof fetch>();
beforeEach(() => { jest.clearAllMocks(); globalThis.fetch = mockFetch as typeof fetch; });
afterEach(() => { globalThis.fetch = originalFetch; jest.useRealTimers(); });
describe("LIB-1 공개 조회 경계 / AC-UI", () => {
  test("검색어 인코딩, 페이지 전달, 인증 헤더 없음", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ items: [], next_start: null, source: "cache", fallback_reason: "not_configured" }) } as Response);
    expect((await searchBooks("한강 & 책", 21, new AbortController().signal)).items).toEqual([]);
    expect(mockFetch.mock.calls[0]![0]).toContain(`/search?q=${encodeURIComponent("한강 & 책")}&start=21`);
    expect(mockFetch.mock.calls[0]![1]?.headers).toBeUndefined();
  });
  test("429·손상 응답·비 JSON은 빈 성공으로 바꾸지 않음", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({ error: { code: "PROVIDER_LIMIT", message: "지금은 조회가 많아요." } }) } as Response);
    await expect(recommendBooks(undefined, true, new AbortController().signal)).rejects.toThrow("지금은 조회가 많아요.");
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) } as Response);
    await expect(searchBooks("책", 1, new AbortController().signal)).rejects.toThrow("응답을 확인하지 못했어요.");
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => { throw new SyntaxError(); } } as unknown as Response);
    await expect(fetchBook("bad", new AbortController().signal)).rejects.toThrow("응답을 확인하지 못했어요.");
  });
  test("시간 초과와 화면 취소가 실제 fetch signal에 전달", async () => {
    jest.useFakeTimers();
    mockFetch.mockImplementation(async (_url, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new Error("abort")), { once: true });
    }));
    const parent = new AbortController();
    const pending = fetchBook("9788936434267", parent.signal);
    const check = expect(pending).rejects.toThrow("조회 시간이 지났어요.");
    await jest.advanceTimersByTimeAsync(BOOK_REQUEST_TIMEOUT_MS);
    await check;
    const next = fetchBook("9788936434267", parent.signal);
    const nextCheck = expect(next).rejects.toThrow();
    parent.abort(); await nextCheck;
    expect(mockFetch.mock.calls[1]![1]?.signal?.aborted).toBe(true);
    expect(jest.getTimerCount()).toBe(0);
  });
});
