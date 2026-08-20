import { ChatShell } from "@/features/chat/components/chat-shell";

export default function ChatPage() {
  return (
    <main className="min-h-dvh bg-[radial-gradient(circle_at_top,oklch(0.94_0.035_252),transparent_42%)] p-2 sm:p-5 lg:p-8">
      <ChatShell surface="page" />
    </main>
  );
}
