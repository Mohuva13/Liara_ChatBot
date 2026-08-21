import { describe, expect, it } from "vitest";

import { isThemePreference } from "./theme-provider";

describe("theme preference", () => {
  it.each(["system", "light", "dark"])("accepts %s", (theme) => {
    expect(isThemePreference(theme)).toBe(true);
  });

  it.each([null, "", "auto", "sepia"])("rejects %s", (theme) => {
    expect(isThemePreference(theme)).toBe(false);
  });
});
