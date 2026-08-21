import type { Metadata } from "next";

import { DirectionProvider } from "@/components/ui/direction";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatProvider } from "@/features/chat/chat-provider";
import { ChatPopup } from "@/features/chat/components/chat-popup";
import { ThemeProvider } from "@/features/theme/theme-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "دستیار مستندات لیارا",
  description: "پاسخ مستند به پرسش‌های فنی درباره خدمات لیارا",
};

const themeScript = `(() => {
  try {
    const stored = localStorage.getItem("liara-assistant-theme");
    const theme = stored === "light" || stored === "dark" ? stored : "system";
    const resolved = theme === "system"
      ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.style.colorScheme = resolved;
  } catch {}
})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <ThemeProvider>
          <DirectionProvider direction="rtl">
            <TooltipProvider>
              <ChatProvider>
                {children}
                <ChatPopup />
              </ChatProvider>
            </TooltipProvider>
          </DirectionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
