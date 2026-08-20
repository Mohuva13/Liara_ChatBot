import type { Metadata } from "next";

import { DirectionProvider } from "@/components/ui/direction";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatProvider } from "@/features/chat/chat-provider";
import { ChatPopup } from "@/features/chat/components/chat-popup";

import "./globals.css";

export const metadata: Metadata = {
  title: "دستیار مستندات لیارا",
  description: "پاسخ مستند به پرسش‌های فنی درباره خدمات لیارا",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fa" dir="rtl">
      <body>
        <DirectionProvider direction="rtl">
          <TooltipProvider>
            <ChatProvider>
              {children}
              <ChatPopup />
            </ChatProvider>
          </TooltipProvider>
        </DirectionProvider>
      </body>
    </html>
  );
}
