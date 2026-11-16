import { describe, expect, test } from "@jest/globals";
import { contrastRatio, darken, getTheme, onFill, theme } from "..";
import { LOOK_BASE_COLORS, LookPreset, ON_FILL_LIGHT, TEXT_COLOR } from "../tokens";

describe("DEF-019 공용 디자인 토큰", () => {
  test("기본 warm 파생색은 시안의 채널 반올림 규칙을 따른다", () => {
    expect(theme.look).toBe("warm");
    expect(theme.colors.textSub).toBe("#71716F");
    expect(theme.colors.divider).toBe("#C4C4C1");
    expect(darken("#FFFFFF", 0)).toBe("#FFFFFF");
    expect(darken("#FFFFFF", 1)).toBe("#000000");
  });

  test.each<LookPreset>(["warm", "toffee", "oxford", "modern"])(
    "%s 룩의 색·곡률을 함께 선택하고 다른 룩 조회에 영향받지 않는다",
    (look) => {
      const selected = getTheme(look);
      expect(selected.colors.bg).toBe(LOOK_BASE_COLORS[look].bg);
      expect(selected.colors.textSub).toBe(darken(selected.colors.bg, 0.5));
      expect(selected.colors.divider).toBe(darken(selected.colors.bg, 0.13));
      expect(selected.radii.card).toBe(look === "modern" ? 6 : 18);
      expect(selected.radii.bookCover).toEqual(look === "modern" ? [2, 4, 4, 2] : [5, 9, 9, 5]);
      expect(selected.radii.control).toBe(9999);
      getTheme(look === "modern" ? "warm" : "modern");
      expect(selected.look).toBe(look);
      expect(theme.look).toBe("warm");
    }
  );

  test("대비는 대칭이며 밝고 어두운 채움에서 글자색 선택이 바뀐다", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21);
    expect(contrastRatio("#FFFFFF", "#000000")).toBeCloseTo(21);
    expect(contrastRatio("#123456", "#123456")).toBe(1);
    expect(onFill(getTheme("warm").colors.fill1)).toBe(TEXT_COLOR);
    expect(onFill(getTheme("oxford").colors.fill1)).toBe(ON_FILL_LIGHT);
    for (const colors of Object.values(LOOK_BASE_COLORS)) {
      for (const fill of [colors.fill1, colors.fill2, colors.fill3, colors.inkStrong]) {
        const chosen = onFill(fill);
        const other = chosen === TEXT_COLOR ? ON_FILL_LIGHT : TEXT_COLOR;
        expect(contrastRatio(fill, chosen)).toBeGreaterThanOrEqual(contrastRatio(fill, other));
      }
    }
  });
});
