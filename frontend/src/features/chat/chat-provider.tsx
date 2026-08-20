"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from "react";

type ChatContextValue = ReturnType<typeof useChat<UIMessage>>;

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: PropsWithChildren) {
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat",
        credentials: "same-origin",
      }),
    [],
  );
  const chat = useChat({ id: "liara-documentation-assistant", transport });

  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useLiaraChat(): ChatContextValue {
  const value = useContext(ChatContext);
  if (value === null) {
    throw new Error("useLiaraChat must be used inside ChatProvider");
  }
  return value;
}
