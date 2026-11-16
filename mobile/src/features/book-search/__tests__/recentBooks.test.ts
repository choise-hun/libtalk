import { beforeEach, describe, expect, jest, test } from "@jest/globals";
import { deviceStorage } from "../../../lib/platform";
import { Book } from "../api";
import { loadRecent, updateRecent } from "../recentBooks";

jest.mock("../../../lib/platform", () => ({ deviceStorage: { getItem: jest.fn(), setItem: jest.fn() } }));
const storage = jest.mocked(deviceStorage);
const values = new Map<string, string>();
export const book = (id: number): Book => ({ isbn13: String(9780000000000 + id), title: `책 ${id}`, author: "저자", publisher: null, cover_url: null, source: "manual" });
beforeEach(() => {
  values.clear(); jest.clearAllMocks();
  storage.getItem.mockImplementation(async key => values.get(key) ?? null);
  storage.setItem.mockImplementation(async (key, value) => { values.set(key, value); });
});
describe("LIB-1 최근 본 도서 / AC-UI·AC-AUTH", () => {
  test("20권 제한, 재열람 맨 앞, 개별·전체 삭제", async () => {
    for (let i = 0; i < 22; i++) await updateRecent("A", { add: book(i) });
    expect((await loadRecent("A")).map(b => b.title)).toEqual(Array.from({ length: 20 }, (_, i) => `책 ${21 - i}`));
    await updateRecent("A", { add: book(5) });
    expect((await loadRecent("A"))[0]?.title).toBe("책 5");
    expect((await loadRecent("A"))).toHaveLength(20);
    await updateRecent("A", { remove: book(5).isbn13 });
    expect((await loadRecent("A")).some(b => b.title === "책 5")).toBe(false);
    expect(await updateRecent("A", { clear: true })).toEqual([]);
    expect(await loadRecent("A")).toEqual([]);
  });
  test("계정 A·B·비로그인 키 분리 및 기기 재열람", async () => {
    await updateRecent("A", { add: book(1) });
    await updateRecent("B", { add: book(2) });
    await updateRecent(null, { add: book(3) });
    expect((await loadRecent("A"))[0]?.title).toBe("책 1");
    expect((await loadRecent("B"))[0]?.title).toBe("책 2");
    expect((await loadRecent(null))[0]?.title).toBe("책 3");
  });
  test("느린 저장 중 연속 추가·전체 삭제도 순서 보장", async () => {
    let release!: () => void;
    storage.setItem.mockImplementationOnce(async (key, value) => {
      await new Promise<void>(resolve => { release = resolve; }); values.set(key, value);
    });
    const first = updateRecent("A", { add: book(1) });
    // 저장이 시작될 때까지 마이크로태스크를 진행한다.
    for (let i = 0; i < 10 && !release; i++) await Promise.resolve();
    const second = updateRecent("A", { add: book(2) });
    const clear = updateRecent("A", { clear: true });
    release(); await Promise.all([first, second, clear]);
    expect(await loadRecent("A")).toEqual([]);
  });
  test("저장 실패·손상은 빈 성공으로 숨기지 않고 전체 삭제로 복구", async () => {
    storage.setItem.mockRejectedValueOnce(new Error("quota"));
    await expect(updateRecent("A", { add: book(1) })).rejects.toThrow("quota");
    storage.getItem.mockResolvedValueOnce("broken");
    await expect(loadRecent("A")).rejects.toThrow();
    await updateRecent("A", { clear: true });
    expect(await loadRecent("A")).toEqual([]);
  });
});
