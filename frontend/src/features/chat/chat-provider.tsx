"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import type { LiaraUIMessage } from "@/features/chat/types/messages";

export type KnowledgeLevel = "beginner" | "intermediate" | "advanced";

type ChatContextValue = ReturnType<typeof useChat<LiaraUIMessage>> & {
  knowledgeLevel: KnowledgeLevel;
  setKnowledgeLevel: (level: KnowledgeLevel) => void;
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: PropsWithChildren) {
  const [knowledgeLevel, setKnowledgeLevel] =
    useState<KnowledgeLevel>("intermediate");
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat",
        credentials: "same-origin",
      }),
    [],
  );
  const chat = useChat<LiaraUIMessage>({
    id: "liara-documentation-assistant",
    transport,
  });

  const value = useMemo(
    () => ({ ...chat, knowledgeLevel, setKnowledgeLevel }),
    [chat, knowledgeLevel],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useLiaraChat(): ChatContextValue {
  const value = useContext(ChatContext);
  if (value === null) {
    throw new Error("useLiaraChat must be used inside ChatProvider");
  }
  return value;
}
