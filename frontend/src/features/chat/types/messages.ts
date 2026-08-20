import type { UIMessage } from "ai";

export type StatusData = {
  text: string;
};

export type SuggestionsData = {
  items: string[];
};

export type SupportData = {
  reasonCode: string;
  ticketUrl: string;
  summary: string;
  text: string;
};

export type UsageData = {
  modelTier: "small" | "large" | "none";
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
  cacheHit: boolean;
};

export type SourceDetail = {
  id: string;
  title: string;
  url: string;
  section: string;
  snippet: string;
  sourceCommit: string;
};

export type LiaraDataTypes = {
  status: StatusData;
  suggestions: SuggestionsData;
  support: SupportData;
  usage: UsageData;
  sourceDetails: { items: SourceDetail[] };
};

export type LiaraUIMessage = UIMessage<unknown, LiaraDataTypes>;
