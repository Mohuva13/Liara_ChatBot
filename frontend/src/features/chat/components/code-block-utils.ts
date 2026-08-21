const LANGUAGE_EXTENSIONS: Record<string, string> = {
  bash: "sh",
  css: "css",
  dockerfile: "dockerfile",
  html: "html",
  javascript: "js",
  js: "js",
  json: "json",
  jsx: "jsx",
  markdown: "md",
  md: "md",
  python: "py",
  py: "py",
  shell: "sh",
  sh: "sh",
  sql: "sql",
  text: "txt",
  ts: "ts",
  tsx: "tsx",
  typescript: "ts",
  yaml: "yaml",
  yml: "yml",
};

export function codeFilename(language: string): string {
  const normalized = language.toLowerCase();
  const extension = LANGUAGE_EXTENSIONS[normalized] ?? "txt";
  return extension === "dockerfile" ? "Dockerfile" : `liara-example.${extension}`;
}
