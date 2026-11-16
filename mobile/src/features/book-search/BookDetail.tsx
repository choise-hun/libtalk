import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";
import { registerSignOutCleanup, useAuth } from "../../auth/AuthProvider";
import { Book, fetchBook } from "./api";
import { BookCover } from "./BookCard";
import { updateRecent } from "./recentBooks";
import { Action, styles } from "./SearchScreen";

type Props = { isbn13: string; fromSearch: boolean; libraryId?: string };
export default function BookDetail(props: Props) {
  const { status, userId } = useAuth();
  const identity = status === "signedIn" ? userId : null;
  const origin = useRef<{ userId: string | null } | null>(null);
  if (status === "loading") return <ActivityIndicator accessibilityLabel="로그인 상태 확인 중" />;
  if (!origin.current) origin.current = { userId: identity };
  return <DetailContent key={`${status}:${userId}:${props.isbn13}:${props.fromSearch}`} {...props} fromSearch={props.fromSearch && origin.current.userId === identity} userId={identity} />;
}
function DetailContent({ isbn13, fromSearch, userId }: Props & { userId: string | null }) {
  const [book, setBook] = useState<Book | null>(null);
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [suspended, setSuspended] = useState(false);
  const active = useRef(true);
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    active.current = true;
    const controller = new AbortController();
    request.current = controller;
    let current = true;
    setBook(null); setError(""); setSaveError("");
    void fetchBook(isbn13, controller.signal).then(async data => {
      if (!current || !active.current) return;
      setBook(data);
      if (fromSearch) {
        try { await updateRecent(userId, { add: data }); }
        catch { if (current && active.current) setSaveError("최근 본 도서를 저장하지 못했어요."); }
      }
    }).catch(e => { if (current && active.current) setError(e instanceof Error ? e.message : "도서를 불러오지 못했어요."); });
    return () => { current = false; active.current = false; controller.abort(); };
  }, [isbn13, fromSearch, userId, attempt]);
  useEffect(() => registerSignOutCleanup(() => { active.current = false; request.current?.abort(); setSuspended(true); setBook(null); }), []);
  return <View style={styles.page}><ScrollView contentContainerStyle={{ padding: 24, maxWidth: 760, width: "100%", alignSelf: "center", gap: 16 }}>
    {suspended ? <Text style={styles.text}>로그인 상태를 바꾸는 중이에요.</Text> : <>
      {!book && !error && <ActivityIndicator accessibilityLabel="도서 상세 불러오는 중" />}
      {!!error && <><Text accessibilityRole="alert" style={styles.text}>{error}</Text><Action label="다시 시도" onPress={() => setAttempt(x => x + 1)} /></>}
      {book && <>
        <BookCover book={book} />
        <Text style={styles.heading}>{book.title}</Text>
        <Text style={styles.text}>{book.author ?? "저자 정보 없음"}</Text>
        <Text style={styles.sub}>{book.publisher ?? "출판사 정보 없음"}</Text>
        <Text style={styles.sub}>ISBN {book.isbn13}</Text>
        <Text style={styles.sub}>서지 출처: {({ naver: "네이버", data4library: "정보나루", manual: "시드·수동 등록" })[book.source]}</Text>
        {!!saveError && <><Text accessibilityRole="alert" style={styles.text}>{saveError}</Text><Action label="최근 도서 저장 다시 시도" onPress={() => {
          void updateRecent(userId, { add: book }).then(() => { if (active.current) setSaveError(""); }).catch(() => { if (active.current) setSaveError("최근 본 도서를 저장하지 못했어요."); });
        }} /></>}
      </>}
    </>}
  </ScrollView></View>;
}
