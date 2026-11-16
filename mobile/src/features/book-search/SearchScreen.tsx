import { useFocusEffect, useRouter } from "expo-router";
import { ComponentRef, useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { registerSignOutCleanup, useAuth } from "../../auth/AuthProvider";
import { theme } from "../../theme";
import { Book, Recommendations, recommendBooks, SearchResult, searchBooks } from "./api";
import { BookCard } from "./BookCard";
import { loadRecent, updateRecent } from "./recentBooks";

export default function SearchScreen({ libraryId }: { libraryId?: string }) {
  const { status, userId } = useAuth();
  if (status === "loading") return <ActivityIndicator accessibilityLabel="로그인 상태 확인 중" />;
  return <SearchContent key={`${status}:${userId}:${libraryId}`} userId={status === "signedIn" ? userId : null} libraryId={libraryId} />;
}
function SearchContent({ userId, libraryId }: { userId: string | null; libraryId?: string }) {
  const router = useRouter();
  const input = useRef<ComponentRef<typeof TextInput>>(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"entry" | "search" | "popular">("entry");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendations | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<Book[]>([]);
  const [recentError, setRecentError] = useState("");
  const [recentBusy, setRecentBusy] = useState(true);
  const [suspended, setSuspended] = useState(false);
  const sequence = useRef(0);
  const historySequence = useRef(0);
  const request = useRef<AbortController | null>(null);
  const latestQuery = useRef("");
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const load = useCallback(async (nextMode: typeof mode, q = "", start = 1) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const generation = ++sequence.current;
    setBusy(true); setError("");
    if (start === 1) { setResult(null); setRecommendation(null); }
    try {
      if (nextMode === "search") {
        const data = await searchBooks(q, start, controller.signal);
        if (generation !== sequence.current) return;
        setResult(old => start === 1 ? data : { ...data, items: [...(old?.items ?? []), ...data.items].filter((b, i, all) => all.findIndex(x => x.isbn13 === b.isbn13) === i) });
      } else {
        const data = await recommendBooks(libraryId, nextMode === "popular", controller.signal);
        if (generation !== sequence.current) return;
        setRecommendation(data);
      }
    } catch (e) {
      if (generation === sequence.current) setError(e instanceof Error ? e.message : "정보를 가져오지 못했어요.");
    } finally { if (generation === sequence.current) setBusy(false); }
  }, [libraryId]);
  const refreshRecent = useCallback(async () => {
    const generation = ++historySequence.current;
    setRecentBusy(true); setRecentError("");
    try {
      const books = await loadRecent(userId);
      if (generation === historySequence.current) setRecent(books);
    } catch { if (generation === historySequence.current) setRecentError("최근 본 도서를 불러오지 못했어요."); }
    finally { if (generation === historySequence.current) setRecentBusy(false); }
  }, [userId]);
  useEffect(() => {
    void load("entry");
    return () => { ++sequence.current; ++historySequence.current; request.current?.abort(); };
  }, [load]);
  useFocusEffect(useCallback(() => {
    if (!suspended) { void refreshRecent(); if (modeRef.current === "entry") input.current?.focus(); }
    return () => { ++historySequence.current; };
  }, [refreshRecent, suspended]));
  useEffect(() => registerSignOutCleanup(() => {
    ++sequence.current; ++historySequence.current; request.current?.abort();
    setSuspended(true); setRecent([]); setResult(null); setRecommendation(null); setQuery("");
  }), []);

  async function remove(isbn13?: string) {
    const generation = ++historySequence.current;
    setRecentBusy(true); setRecentError("");
    try {
      const books = await updateRecent(userId, isbn13 ? { remove: isbn13 } : { clear: true });
      if (generation === historySequence.current) setRecent(books);
    } catch { if (generation === historySequence.current) setRecentError("최근 본 도서를 삭제하지 못했어요. 다시 시도해 주세요."); }
    finally { if (generation === historySequence.current) setRecentBusy(false); }
  }
  function switchMode(next: typeof mode) {
    setMode(next); void load(next, latestQuery.current);
  }
  function submit() {
    const q = query.trim();
    if (!q || q.length > 100) { setError("검색어를 1~100자로 입력해 주세요."); return; }
    latestQuery.current = q; setMode("search"); void load("search", q);
  }
  function open(book: Book, fromSearch: boolean) {
    router.push({ pathname: "/books/[isbn13]", params: { isbn13: book.isbn13, ...(libraryId ? { library_id: libraryId } : {}), ...(fromSearch ? { from: "search" } : {}) } });
  }
  if (suspended) return <View style={styles.page}><Text style={styles.text}>로그인 상태를 바꾸는 중이에요.</Text></View>;
  return <KeyboardAvoidingView behavior="padding" style={styles.page}>
    <View style={styles.content}>
      <Text style={styles.heading}>다음 한 권을 찾아보세요</Text>
      <Text style={styles.sub}>{userId ? "계정별 최근 본 도서 · 이 기기에 저장" : "로그인 없이 둘러볼 수 있어요 · 최근 도서는 이 기기에만 저장"}</Text>
      <View style={styles.searchRow}>
        <TextInput ref={input} autoFocus accessibilityLabel="도서 검색어" placeholder="제목, 저자 또는 ISBN" placeholderTextColor={theme.colors.textSub} value={query} maxLength={100} returnKeyType="search" onChangeText={value => {
          setQuery(value);
          // 입력을 바꾼 즉시 예전 검색/추가 페이지의 응답을 무효화한다.
          if (mode === "search") { setMode("entry"); void load("entry"); }
        }} onSubmitEditing={submit} style={styles.input} />
        <Action label="검색" onPress={submit} />
      </View>
      <View style={styles.searchRow}>
        <Action label="추천·최근 본 도서" onPress={() => switchMode("entry")} />
        <Action label="인기 도서 탐색" onPress={() => switchMode("popular")} />
      </View>
      <ScrollView keyboardShouldPersistTaps="handled" keyboardDismissMode="none" contentContainerStyle={styles.scroll}>
        {busy && <ActivityIndicator accessibilityLabel="도서 불러오는 중" color={theme.colors.inkStrong} />}
        {!!error && <View accessibilityRole="alert"><Text style={styles.text}>{error}</Text><Action label="다시 시도" disabled={busy} onPress={() => void load(mode, latestQuery.current, result?.next_start ?? 1)} /></View>}
        {mode !== "search" && recommendation && <>
          <Text style={styles.section}>{recommendation.kind === "theme" ? "테마 추천" : "인기 도서"}</Text>
          <Text style={styles.text}>{recommendation.basis_label}</Text>
          {recommendation.theme?.description && <Text style={styles.sub}>{recommendation.theme.description}</Text>}
          <Text style={styles.sub}>{recommendation.kind === "popular" ? "출처: 정보나루 · 인기 순위이며 대출 가능 표시가 아니에요." : "운영자가 고른 책이에요."}</Text>
          {recommendation.fetched_at && <Text style={styles.sub}>조회 시각 {recommendation.fetched_at}{recommendation.stale ? " · 오래된 캐시" : ""}</Text>}
          {recommendation.fallback_reason && <Text style={styles.sub}>제공자 조회를 대신해 저장된 자료를 보여드려요.{recommendation.scope === "national" && libraryId ? " 전국 기준으로 대체했어요." : ""}</Text>}
          {!recommendation.books.length && <Text style={styles.text}>추천 도서를 찾지 못했어요.</Text>}
          {recommendation.books.map(book => <BookCard key={book.isbn13} book={book} onPress={() => open(book, false)} />)}
        </>}
        {mode === "search" && result && <>
          <Text style={styles.section}>검색 결과</Text>
          <Text style={styles.sub}>{result.source === "cache" ? "저장된 서지에서 검색했어요." : "출처: 네이버 도서 검색"}</Text>
          {!result.items.length && <Text style={styles.text}>찾지 못했어요. 다른 검색어로 찾아보세요.</Text>}
          {result.items.map(book => <BookCard key={book.isbn13} book={book} onPress={() => open(book, true)} />)}
          {result.next_start !== null && <Action label="더 보기" disabled={busy} onPress={() => void load("search", latestQuery.current, result.next_start!)} />}
        </>}
        {mode === "entry" && <>
          <Text style={styles.section}>최근 본 도서</Text>
          <Action label="전체 삭제" disabled={recentBusy} onPress={() => void remove()} />
          {recentBusy && <ActivityIndicator accessibilityLabel="최근 본 도서 불러오는 중" />}
          {!!recentError && <><Text style={styles.text} accessibilityRole="alert">{recentError}</Text><Action label="최근 도서 다시 시도" onPress={() => void refreshRecent()} /></>}
          {!recentBusy && !recentError && !recent.length && <Text style={styles.text}>검색 결과에서 상세를 연 책이 여기에 쌓여요.</Text>}
          {recent.map(book => <BookCard key={book.isbn13} book={book} onPress={() => open(book, false)} onRemove={() => void remove(book.isbn13)} />)}
        </>}
      </ScrollView>
    </View>
  </KeyboardAvoidingView>;
}
export function Action({ label, onPress, disabled = false }: { label: string; onPress: () => void; disabled?: boolean }) {
  return <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={styles.action}><Text style={[styles.link, disabled && { opacity: 0.45 }]}>{label}</Text></Pressable>;
}
export const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.bg },
  content: { flex: 1, width: "100%", maxWidth: 760, alignSelf: "center", paddingHorizontal: 20, paddingTop: 16 },
  heading: { fontSize: 24, fontWeight: "700", color: theme.colors.text, marginBottom: 8 },
  section: { fontSize: 20, fontWeight: "700", color: theme.colors.text, marginTop: 24, marginBottom: 10 },
  text: { color: theme.colors.text, fontSize: 16, lineHeight: 25 },
  sub: { color: theme.colors.textSub, fontSize: 13, lineHeight: 21 },
  searchRow: { flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8, marginTop: 12 },
  input: { flex: 1, minWidth: 150, padding: 14, color: theme.colors.text, backgroundColor: theme.colors.paper, borderRadius: theme.radii.card, fontSize: 16 },
  action: { paddingVertical: 12, paddingHorizontal: 8 },
  link: { color: theme.colors.inkStrong, fontSize: 15, fontWeight: "700" },
  scroll: { paddingBottom: 40 },
});
