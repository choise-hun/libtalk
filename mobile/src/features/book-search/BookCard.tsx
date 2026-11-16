import { useState } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { theme } from "../../theme";
import { Book } from "./api";

export function BookCover({ book }: { book: Book }) {
  const [failed, setFailed] = useState(false);
  return book.cover_url && !failed ?
    <Image key={book.cover_url} accessibilityLabel={`${book.title} 표지`} source={{ uri: book.cover_url }} onError={() => setFailed(true)} style={styles.cover} /> :
    <View style={[styles.cover, styles.fallback]}><Text style={styles.title}>{book.title}</Text><Text style={styles.sub}>{book.author ?? "저자 정보 없음"}</Text></View>;
}
export function BookCard({ book, onPress, onRemove }: { book: Book; onPress: () => void; onRemove?: () => void }) {
  return <View style={styles.row}>
    <Pressable accessibilityRole="button" accessibilityLabel={`${book.title} 상세 보기`} onPress={onPress} style={styles.main}>
      <BookCover key={book.isbn13} book={book} />
      <View style={styles.info}><Text style={styles.title}>{book.title}</Text><Text style={styles.sub}>{book.author ?? "저자 정보 없음"}</Text><Text style={styles.sub}>{book.publisher ?? "출판사 정보 없음"}</Text></View>
    </Pressable>
    {onRemove && <Pressable accessibilityRole="button" accessibilityLabel={`${book.title} 최근 목록에서 삭제`} onPress={onRemove} style={styles.remove}><Text style={styles.sub}>삭제</Text></Pressable>}
  </View>;
}
const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 12, borderBottomWidth: 1, borderColor: theme.colors.divider },
  main: { flex: 1, flexDirection: "row", alignItems: "center", gap: 16 },
  info: { flex: 1, gap: 6 },
  cover: { width: 82, height: 118, backgroundColor: theme.colors.fill3, borderTopLeftRadius: theme.radii.bookCover[0], borderTopRightRadius: theme.radii.bookCover[1], borderBottomRightRadius: theme.radii.bookCover[2], borderBottomLeftRadius: theme.radii.bookCover[3] },
  fallback: { padding: 8, justifyContent: "space-between", overflow: "hidden" },
  title: { color: theme.colors.text, fontWeight: "700", fontSize: 16 },
  sub: { color: theme.colors.textSub, fontSize: 13 },
  remove: { padding: 12 },
});
