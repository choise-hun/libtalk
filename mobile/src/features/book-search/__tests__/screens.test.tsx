import { beforeEach, describe, expect, jest, test } from "@jest/globals";
import { act, fireEvent, render, waitFor } from "@testing-library/react-native";
import React from "react";
import SearchScreen from "../SearchScreen";
import BookDetail from "../BookDetail";
import { Book, fetchBook, Recommendations, recommendBooks, searchBooks, SearchResult } from "../api";
import { loadRecent, updateRecent } from "../recentBooks";
import { useAuth } from "../../../auth/AuthProvider";

const mockPush = jest.fn();
const mockCleanups = new Set<() => void>();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush }),
  useFocusEffect: (callback: () => void) => { const ReactLib = require("react"); ReactLib.useEffect(callback, [callback]); },
}));
jest.mock("../../../auth/AuthProvider", () => ({ useAuth: jest.fn(), registerSignOutCleanup: (fn: () => void) => { mockCleanups.add(fn); return () => mockCleanups.delete(fn); } }));
jest.mock("../api", () => ({ searchBooks: jest.fn(), recommendBooks: jest.fn(), fetchBook: jest.fn() }));
jest.mock("../recentBooks", () => ({ loadRecent: jest.fn(), updateRecent: jest.fn() }));
const b: Book = { isbn13: "9788936434267", title: "채식주의자", author: "한강", publisher: "창비", cover_url: null, source: "manual" };
const rec: Recommendations = { kind: "theme", scope: "national", library_id: null, basis_label: "오늘의 테마", theme: { id: 1, title: "오늘의 테마", description: "소개" }, books: [b], fetched_at: null, stale: false, fallback_reason: null };
const result: SearchResult = { items: [b], next_start: null, source: "cache", fallback_reason: "not_configured" };
const mockedAuth = jest.mocked(useAuth);
function deferred<T>() { let resolve!: (data: T) => void; let reject!: (e: Error) => void; const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }
beforeEach(() => {
  jest.clearAllMocks(); mockCleanups.clear();
  mockedAuth.mockReturnValue({ status: "signedOut", userId: null } as ReturnType<typeof useAuth>);
  jest.mocked(recommendBooks).mockResolvedValue(rec);
  jest.mocked(searchBooks).mockResolvedValue(result);
  jest.mocked(fetchBook).mockResolvedValue(b);
  jest.mocked(loadRecent).mockResolvedValue([]);
  jest.mocked(updateRecent).mockResolvedValue([b]);
});
describe("LIB-1 / AC-UI·AC-RACE·AC-AUTH", () => {
  test("비로그인 진입·추천·최근 빈 상태, 검색 상세 경로에만 기록 표시", async () => {
    const ui = await render(<SearchScreen libraryId="7" />);
    await waitFor(() => expect(ui.getByText("오늘의 테마")).toBeTruthy());
    expect(ui.getByLabelText("도서 검색어").props.autoFocus).toBe(true);
    expect(ui.getByText(/로그인 없이/)).toBeTruthy();
    expect(ui.getByText(/검색 결과에서 상세를 연 책/)).toBeTruthy();
    await fireEvent.press(ui.getByLabelText("채식주의자 상세 보기"));
    expect(mockPush).toHaveBeenLastCalledWith({ pathname: "/books/[isbn13]", params: { isbn13: b.isbn13, library_id: "7" } });
    await fireEvent.changeText(ui.getByLabelText("도서 검색어"), "한강");
    await fireEvent.press(ui.getByText("검색"));
    await waitFor(() => expect(ui.getByText("검색 결과")).toBeTruthy());
    await fireEvent.press(ui.getByLabelText("채식주의자 상세 보기"));
    expect(mockPush).toHaveBeenLastCalledWith({ pathname: "/books/[isbn13]", params: { isbn13: b.isbn13, library_id: "7", from: "search" } });
    expect(updateRecent).not.toHaveBeenCalled();
  });
  test("추천 실패 오류·재시도, 인기 탐색은 도서관 범위 전달·기준·오래된 캐시 표시", async () => {
    jest.mocked(recommendBooks).mockRejectedValueOnce(new Error("추천 실패"));
    const ui = await render(<SearchScreen libraryId="7" />);
    await waitFor(() => expect(ui.getByText("추천 실패")).toBeTruthy());
    await fireEvent.press(ui.getByText("다시 시도"));
    await waitFor(() => expect(ui.getByText("오늘의 테마")).toBeTruthy());
    jest.mocked(recommendBooks).mockResolvedValue({ ...rec, kind: "popular", theme: null, stale: true, fetched_at: "2026-11-15T10:00:00+09:00", basis_label: "전국 · 최근 30일", fallback_reason: "no_data" });
    await fireEvent.press(ui.getByText("인기 도서 탐색"));
    await waitFor(() => expect(ui.getByText("전국 · 최근 30일")).toBeTruthy());
    expect(recommendBooks).toHaveBeenLastCalledWith("7", true, expect.any(AbortSignal));
    expect(ui.getByText(/오래된 캐시/)).toBeTruthy(); expect(ui.getByText(/전국 기준으로 대체/)).toBeTruthy();
  });
  test("검색어 전환 후 늦은 성공·실패와 취소한 이전 요청이 현재 결과를 덮지 않음", async () => {
    const old = deferred<SearchResult>();
    jest.mocked(searchBooks).mockReturnValueOnce(old.promise).mockResolvedValueOnce({ ...result, items: [{ ...b, title: "새 책" }] });
    const ui = await render(<SearchScreen />);
    await fireEvent.changeText(ui.getByLabelText("도서 검색어"), "이전"); await fireEvent.press(ui.getByText("검색"));
    const oldSignal = jest.mocked(searchBooks).mock.calls[0]![2];
    await fireEvent.changeText(ui.getByLabelText("도서 검색어"), "새 검색"); await fireEvent.press(ui.getByText("검색"));
    await waitFor(() => expect(ui.getByLabelText("새 책 상세 보기")).toBeTruthy());
    expect(oldSignal.aborted).toBe(true);
    await act(async () => old.reject(new Error("늦은 오류")));
    expect(ui.queryByText("늦은 오류")).toBeNull(); expect(ui.getByLabelText("새 책 상세 보기")).toBeTruthy();
  });
  test("페이지 추가 실패 후 같은 cursor 재시도, 기존 목록 유지", async () => {
    jest.mocked(searchBooks).mockResolvedValueOnce({ ...result, next_start: 21 }).mockRejectedValueOnce(new Error("추가 실패")).mockResolvedValueOnce({ ...result, items: [{ ...b, isbn13: "9788936434120", title: "추가 책" }] });
    const ui = await render(<SearchScreen />);
    await fireEvent.changeText(ui.getByLabelText("도서 검색어"), "책"); await fireEvent.press(ui.getByText("검색"));
    await waitFor(() => expect(ui.getByText("더 보기")).toBeTruthy());
    await fireEvent.press(ui.getByText("더 보기")); await waitFor(() => expect(ui.getByText("추가 실패")).toBeTruthy());
    expect(ui.getByLabelText("채식주의자 상세 보기")).toBeTruthy();
    await fireEvent.press(ui.getByText("다시 시도")); await waitFor(() => expect(ui.getByLabelText("추가 책 상세 보기")).toBeTruthy());
    expect(searchBooks).toHaveBeenLastCalledWith("책", 21, expect.any(AbortSignal));
  });
  test("A 최근 목록 지연 중 B 전환: A 도서 미노출 및 로그아웃 정화", async () => {
    const old = deferred<Book[]>();
    mockedAuth.mockReturnValue({ status: "signedIn", userId: "A" } as ReturnType<typeof useAuth>);
    jest.mocked(loadRecent).mockReturnValueOnce(old.promise).mockResolvedValueOnce([]);
    const ui = await render(<SearchScreen />);
    mockedAuth.mockReturnValue({ status: "signedIn", userId: "B" } as ReturnType<typeof useAuth>);
    await ui.rerender(<SearchScreen />);
    await act(async () => old.resolve([{ ...b, title: "A의 최근 책" }]));
    expect(ui.queryByText("A의 최근 책")).toBeNull();
    await act(async () => { mockCleanups.forEach(fn => fn()); });
    expect(ui.queryByText("오늘의 테마")).toBeNull();
  });
  test("검색 빈 결과 안내와 최근 목록 개별·전체 삭제 실패 재시도", async () => {
    jest.mocked(loadRecent).mockResolvedValue([b]);
    jest.mocked(searchBooks).mockResolvedValue({ ...result, items: [] });
    jest.mocked(updateRecent).mockRejectedValueOnce(new Error("quota")).mockResolvedValue([]);
    const ui = await render(<SearchScreen />);
    await waitFor(() => expect(ui.getByLabelText("채식주의자 최근 목록에서 삭제")).toBeTruthy());
    await fireEvent.press(ui.getByLabelText("채식주의자 최근 목록에서 삭제"));
    await waitFor(() => expect(ui.getByText(/삭제하지 못했어요/)).toBeTruthy());
    expect(ui.getByLabelText("채식주의자 최근 목록에서 삭제")).toBeTruthy();
    await fireEvent.press(ui.getByLabelText("채식주의자 최근 목록에서 삭제"));
    await waitFor(() => expect(ui.queryByLabelText("채식주의자 최근 목록에서 삭제")).toBeNull());
    expect(updateRecent).toHaveBeenCalledWith(null, { remove: b.isbn13 });
    await fireEvent.press(ui.getByText("전체 삭제"));
    expect(updateRecent).toHaveBeenLastCalledWith(null, { clear: true });
    await fireEvent.changeText(ui.getByLabelText("도서 검색어"), "못찾을책"); await fireEvent.press(ui.getByText("검색"));
    await waitFor(() => expect(ui.getByText("찾지 못했어요. 다른 검색어로 찾아보세요.")).toBeTruthy());
  });
  test("도서관 전환 뒤 이전 추천 성공 응답 폐기", async () => {
    const old = deferred<Recommendations>();
    jest.mocked(recommendBooks).mockReturnValueOnce(old.promise).mockResolvedValueOnce({ ...rec, basis_label: "새 도서관 테마" });
    const ui = await render(<SearchScreen libraryId="1" />);
    const oldSignal = jest.mocked(recommendBooks).mock.calls[0]![2];
    await ui.rerender(<SearchScreen libraryId="2" />);
    await waitFor(() => expect(ui.getByText("새 도서관 테마")).toBeTruthy());
    await act(async () => old.resolve(rec));
    expect(oldSignal.aborted).toBe(true); expect(ui.queryByText("오늘의 테마")).toBeNull();
  });
  test("상세 성공 후에만 최근 저장, 추천 진입·실패는 저장하지 않음", async () => {
    const ui = await render(<BookDetail isbn13={b.isbn13} fromSearch={false} />);
    await waitFor(() => expect(ui.getByText(`ISBN ${b.isbn13}`)).toBeTruthy());
    expect(updateRecent).not.toHaveBeenCalled();
    await ui.rerender(<BookDetail isbn13={b.isbn13} fromSearch />);
    await waitFor(() => expect(updateRecent).toHaveBeenCalledWith(null, { add: b }));
    jest.mocked(updateRecent).mockClear(); jest.mocked(fetchBook).mockRejectedValueOnce(new Error("찾을 수 없어요."));
    await ui.rerender(<BookDetail isbn13="bad" fromSearch />);
    await waitFor(() => expect(ui.getByText("찾을 수 없어요.")).toBeTruthy());
    expect(updateRecent).not.toHaveBeenCalled();
  });
  test("상세 늦은 응답·계정 변경이 B 최근 기록을 생성하지 않음", async () => {
    const old = deferred<Book>();
    mockedAuth.mockReturnValue({ status: "signedIn", userId: "A" } as ReturnType<typeof useAuth>);
    jest.mocked(fetchBook).mockReturnValueOnce(old.promise).mockResolvedValueOnce(b);
    const ui = await render(<BookDetail isbn13={b.isbn13} fromSearch />);
    mockedAuth.mockReturnValue({ status: "signedIn", userId: "B" } as ReturnType<typeof useAuth>);
    await ui.rerender(<BookDetail isbn13={b.isbn13} fromSearch />);
    await act(async () => old.resolve(b));
    expect(updateRecent).not.toHaveBeenCalled();
  });
});
