import { Stack, useLocalSearchParams } from "expo-router";
import SearchScreen from "../../src/features/book-search/SearchScreen";

export default function Books() {
  const { library_id } = useLocalSearchParams<{ library_id?: string }>();
  return <><Stack.Screen options={{ title: "도서 검색" }} /><SearchScreen libraryId={typeof library_id === "string" ? library_id : undefined} /></>;
}
