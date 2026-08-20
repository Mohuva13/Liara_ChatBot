"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink, LifeBuoy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SupportData } from "@/features/chat/types/messages";

export function SupportCard({ support }: { support: SupportData }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">(
    "idle",
  );

  const copySummary = async () => {
    try {
      await navigator.clipboard.writeText(support.summary);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("failed");
    }
  };

  return (
    <Card className="border-warning/40 bg-warning/5">
      <CardHeader className="gap-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <LifeBuoy aria-hidden="true" className="size-5" />
          ادامه از مسیر پشتیبانی
        </CardTitle>
        <p className="text-sm leading-6 text-muted-foreground">
          {support.text || "برای این مورد پاسخ قابل‌اعتماد کافی پیدا نشد."}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <pre
          className="max-h-44 overflow-auto whitespace-pre-wrap rounded-xl bg-muted p-3 text-xs leading-6"
          dir="auto"
        >
          {support.summary}
        </pre>
        <div className="flex flex-wrap gap-2">
          <Button
            render={
              <a href={support.ticketUrl} rel="noreferrer" target="_blank" />
            }
            size="sm"
          >
              ثبت تیکت
              <ExternalLink aria-hidden="true" />
          </Button>
          <Button onClick={() => void copySummary()} size="sm" variant="outline">
            {copyState === "copied" ? (
              <Check aria-hidden="true" />
            ) : (
              <Copy aria-hidden="true" />
            )}
            {copyState === "copied" ? "کپی شد" : "کپی خلاصه"}
          </Button>
          <span aria-live="polite" className="sr-only">
            {copyState === "copied"
              ? "خلاصه برای تیکت کپی شد"
              : copyState === "failed"
                ? "کپی خلاصه انجام نشد"
                : ""}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
