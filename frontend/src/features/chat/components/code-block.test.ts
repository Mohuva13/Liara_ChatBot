import { describe, expect, it } from "vitest";

import { codeFilename } from "./code-block-utils";

describe("code block downloads", () => {
  it.each([
    ["bash", "liara-example.sh"],
    ["python", "liara-example.py"],
    ["javascript", "liara-example.js"],
    ["json", "liara-example.json"],
    ["yaml", "liara-example.yaml"],
    ["unknown", "liara-example.txt"],
  ])("maps %s to a safe filename", (language, expected) => {
    expect(codeFilename(language)).toBe(expected);
  });
});
