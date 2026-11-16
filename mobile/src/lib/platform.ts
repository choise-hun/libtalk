import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

/** 공개 서지의 기기 저장만 담당. 저장소 오류는 호출자가 안내한다. */
export const deviceStorage = {
  async getItem(key: string): Promise<string | null> {
    if (Platform.OS !== "web") return AsyncStorage.getItem(key);
    return typeof localStorage === "undefined" ? null : localStorage.getItem(key);
  },
  async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS !== "web") return AsyncStorage.setItem(key, value);
    if (typeof localStorage === "undefined") throw new Error("기기 저장소를 사용할 수 없어요.");
    localStorage.setItem(key, value);
  },
};
