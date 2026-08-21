"use client";

import { useState } from "react";

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
import { SourceCards } from "@/features/chat/components/source-cards";
import { SupportCard } from "@/features/chat/components/support-card";
import type { LiaraUIMessage } from "@/features/chat/types/messages";
import { cn } from "@/lib/utils";
import {
  BookOpenText,
  LifeBuoy,
  RefreshCcw,
  RotateCcw,
  Sparkles,
} from "lucide-react";

type ChatSurface = "popup" | "page";

const STARTERS = [
  "چطور یک برنامه Next.js را روی لیارا مستقر کنم؟",
  "برای اتصال امن برنامه به Redis از کدام شبکه استفاده کنم؟",
  "Pgvector در PostgreSQL لیارا چه محدودیتی دارد؟",
];

function MessageSources({ message }: { message: LiaraUIMessage }) {
  const sources = message.parts.filter((part) => part.type === "source-url");
  const details = message.parts
    .filter((part) => part.type === "data-sourceDetails")
    .flatMap((part) => part.data.items);
  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
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
      <SourceCards sources={details} />
    </div>
  );
}

function ChatMessage({
  message,
  onSelect,
}: {
  message: LiaraUIMessage;
  onSelect: (question: string) => void;
}) {
  return (
    <Message from={message.role}>
      <MessageContent>
        {message.parts.map((part, index) => {
          if (part.type === "text") {
            return (
            <MessageResponse
              dir="auto"
              isAnimating={part.state === "streaming"}
              key={`${message.id}-text-${index}`}
            >
              {part.text}
            </MessageResponse>
            );
          }
          if (part.type === "data-support") {
            return (
              <SupportCard
                key={`${message.id}-support-${index}`}
                support={part.data}
              />
            );
          }
          if (part.type === "data-suggestions" && part.data.items.length > 0) {
            return (
              <Suggestions
                className="w-full flex-wrap"
                key={`${message.id}-suggestions-${index}`}
              >
                {part.data.items.map((suggestion) => (
                  <Suggestion
                    key={suggestion}
                    onClick={onSelect}
                    suggestion={suggestion}
                  />
                ))}
              </Suggestions>
            );
          }
          return null;
        })}
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
  const [resetFailed, setResetFailed] = useState(false);
  const {
    clearError,
    error,
    messages,
    regenerate,
    sendMessage,
    setMessages,
    status,
    stop,
  } = useLiaraChat();

  const resetSession = async () => {
    stop();
    setResetFailed(false);
    try {
      const response = await fetch("/api/session", { method: "DELETE" });
      if (!response.ok) {
        throw new Error("session reset failed");
      }
      setMessages([]);
      clearError();
    } catch {
      setResetFailed(true);
    }
  };

  const send = async (text: string) => {
    const normalized = text.trim();
    if (!normalized || status === "submitted" || status === "streaming") {
      return;
    }
    clearError();
    await sendMessage(
      { text: normalized },
      { body: { surface } },
    );
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
      className={cn(
        "mx-auto flex w-full flex-col overflow-hidden border bg-card/95 backdrop-blur",
        surface === "page" &&
          "elevation-chat h-[calc(100dvh-1rem)] max-w-5xl rounded-[var(--radius-popup)] sm:h-[calc(100dvh-2.5rem)] lg:h-[calc(100dvh-4rem)]",
        surface === "popup" && "h-full rounded-[var(--radius-popup)]",
      )}
    >
      <header
        className={cn(
          "flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-6 sm:py-4",
          surface === "popup" && "ps-12",
        )}
      >
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold sm:text-lg">
            دستیار مستندات لیارا
          </h1>
          <p aria-live="polite" className="text-xs text-muted-foreground">
            {statusLabel}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button
            aria-label="شروع گفت‌وگوی جدید"
            onClick={() => void resetSession()}
            size="icon-sm"
            title="شروع گفت‌وگوی جدید"
            type="button"
            variant="ghost"
          >
            <RefreshCcw aria-hidden="true" />
          </Button>
          <div className="hidden items-center gap-2 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary sm:flex">
            <LifeBuoy aria-hidden="true" className="size-4" />
            پاسخ مستند
          </div>
        </div>
      </header>

      {resetFailed ? (
        <p
          className="border-b border-destructive/30 bg-destructive/5 px-4 py-2 text-xs text-destructive"
          role="alert"
        >
          شروع گفت‌وگوی جدید انجام نشد؛ دوباره تلاش کنید.
        </p>
      ) : null}

      <Conversation className="min-h-0">
        <ConversationContent className="mx-auto w-full max-w-3xl gap-6 px-3 py-5 sm:px-6">
          {messages.length === 0 ? (
            <WelcomeState onSelect={(question) => void send(question)} />
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onSelect={(question) => void send(question)}
              />
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
