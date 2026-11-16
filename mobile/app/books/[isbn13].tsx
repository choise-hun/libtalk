import { Stack, useLocalSearchParams } from "expo-router";
import BookDetail from "../../src/features/book-search/BookDetail";

export default function BookPage() {
  const { isbn13, from, library_id } = useLocalSearchParams<{ isbn13: string; from?: string; library_id?: string }>();
  return <><Stack.Screen options={{ title: "도서 상세" }} /><BookDetail isbn13={typeof isbn13 === "string" ? isbn13 : ""} fromSearch={from === "search"} libraryId={typeof library_id === "string" ? library_id : undefined} /></>;
}
