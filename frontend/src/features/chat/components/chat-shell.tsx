"use client";

import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import {
  Suggestion,
  Suggestions,
} from "@/components/ai-elements/suggestion";
import { Button } from "@/components/ui/button";
import { useLiaraChat } from "@/features/chat/chat-provider";
import type { UIMessage } from "ai";
import { BookOpenText, LifeBuoy, RotateCcw, Sparkles } from "lucide-react";

type ChatSurface = "popup" | "page";

const STARTERS = [
  "چطور یک برنامه Next.js را روی لیارا مستقر کنم؟",
  "برای اتصال امن برنامه به Redis از کدام شبکه استفاده کنم؟",
  "Pgvector در PostgreSQL لیارا چه محدودیتی دارد؟",
];

function MessageSources({ message }: { message: UIMessage }) {
  const sources = message.parts.filter((part) => part.type === "source-url");
  if (sources.length === 0) {
    return null;
  }

  return (
    <Sources>
      <SourcesTrigger count={sources.length}>
        {sources.length.toLocaleString("fa-IR")} منبع مستند
      </SourcesTrigger>
      <SourcesContent>
        {sources.map((source) => (
          <Source
            href={source.url}
            key={source.sourceId}
            title={source.title ?? "مستندات لیارا"}
          />
        ))}
      </SourcesContent>
    </Sources>
  );
}

function ChatMessage({ message }: { message: UIMessage }) {
  return (
    <Message from={message.role}>
      <MessageContent>
        {message.parts.map((part, index) =>
          part.type === "text" ? (
            <MessageResponse
              dir="auto"
              isAnimating={part.state === "streaming"}
              key={`${message.id}-text-${index}`}
            >
              {part.text}
            </MessageResponse>
          ) : null,
        )}
      </MessageContent>
      {message.role === "assistant" ? <MessageSources message={message} /> : null}
    </Message>
  );
}

function WelcomeState({ onSelect }: { onSelect: (question: string) => void }) {
  return (
    <section className="m-auto flex w-full max-w-2xl flex-col items-center gap-5 px-2 py-10 text-center sm:py-16">
      <div className="grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
        <Sparkles aria-hidden="true" className="size-7" />
      </div>
      <div className="space-y-2">
        <h2 className="text-balance text-2xl font-semibold sm:text-3xl">
          از مستندات لیارا بپرسید
        </h2>
        <p className="mx-auto max-w-xl text-pretty text-sm leading-7 text-muted-foreground sm:text-base">
          پاسخ فنی فقط با شواهد مستندات رسمی نمایش داده می‌شود. اگر شاهد کافی
          نباشد، سؤال تکمیلی می‌پرسیم یا مسیر پشتیبانی را پیشنهاد می‌کنیم.
        </p>
      </div>
      <Suggestions className="justify-start px-1 sm:w-full sm:flex-wrap sm:justify-center">
        {STARTERS.map((starter) => (
          <Suggestion
            key={starter}
            onClick={onSelect}
            suggestion={starter}
          />
        ))}
      </Suggestions>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <BookOpenText aria-hidden="true" className="size-4" />
        منبع هر پاسخ به‌صورت جداگانه نمایش داده می‌شود.
      </div>
    </section>
  );
}

export function ChatShell({ surface }: { surface: ChatSurface }) {
  const {
    clearError,
    error,
    messages,
    regenerate,
    sendMessage,
    status,
    stop,
  } = useLiaraChat();

  const send = async (text: string) => {
    const normalized = text.trim();
    if (!normalized || status === "submitted" || status === "streaming") {
      return;
    }
    clearError();
    await sendMessage({ text: normalized }, { body: { surface } });
  };

  const statusLabel =
    status === "submitted"
      ? "در حال جست‌وجوی مستندات…"
      : status === "streaming"
        ? "در حال دریافت پاسخ مستند…"
        : "آماده دریافت پرسش";

  return (
    <section
      aria-label="گفت‌وگو با دستیار مستندات لیارا"
      className="mx-auto flex h-[calc(100dvh-1rem)] w-full max-w-5xl flex-col overflow-hidden rounded-[1.75rem] border bg-card/95 shadow-2xl shadow-primary/10 backdrop-blur sm:h-[calc(100dvh-2.5rem)] lg:h-[calc(100dvh-4rem)]"
    >
      <header className="flex items-center justify-between gap-4 border-b px-4 py-3 sm:px-6 sm:py-4">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold sm:text-lg">
            دستیار مستندات لیارا
          </h1>
          <p aria-live="polite" className="text-xs text-muted-foreground">
            {statusLabel}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
          <LifeBuoy aria-hidden="true" className="size-4" />
          پاسخ مستند
        </div>
      </header>

      <Conversation className="min-h-0">
        <ConversationContent className="mx-auto w-full max-w-3xl gap-6 px-3 py-5 sm:px-6">
          {messages.length === 0 ? (
            <WelcomeState onSelect={(question) => void send(question)} />
          ) : (
            messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {error ? (
            <div
              className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm"
              role="alert"
            >
              <p className="font-medium">پاسخ دریافت نشد.</p>
              <p className="mt-1 text-muted-foreground">
                متن پرسش حفظ شده است. می‌توانید پس از آماده‌شدن سرویس دوباره تلاش
                کنید.
              </p>
              <Button
                className="mt-3"
                onClick={() => void regenerate({ body: { surface } })}
                size="sm"
                type="button"
                variant="outline"
              >
                <RotateCcw aria-hidden="true" />
                تلاش دوباره
              </Button>
            </div>
          ) : null}
        </ConversationContent>
        <ConversationScrollButton aria-label="رفتن به آخر گفتگو" />
      </Conversation>

      <footer className="border-t bg-card/98 px-3 py-3 sm:px-6 sm:py-4">
        <PromptInput
          className="mx-auto max-w-3xl"
          onSubmit={({ text }) => send(text)}
        >
          <PromptInputBody>
            <PromptInputTextarea
              aria-label="پرسش درباره خدمات لیارا"
              maxLength={4000}
              placeholder="پرسش خود درباره لیارا را بنویسید…"
            />
          </PromptInputBody>
          <PromptInputFooter>
            <span className="px-1 text-[0.7rem] text-muted-foreground">
              Enter برای ارسال · Shift+Enter برای خط جدید
            </span>
            <PromptInputSubmit
              onStop={stop}
              status={status}
              title={status === "streaming" ? "توقف پاسخ" : "ارسال پرسش"}
            />
          </PromptInputFooter>
        </PromptInput>
      </footer>
    </section>
  );
}
