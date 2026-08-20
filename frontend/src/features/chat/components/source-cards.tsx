import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SourceDetail } from "@/features/chat/types/messages";

export function SourceCards({ sources }: { sources: SourceDetail[] }) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <section aria-label="منابع رسمی پاسخ" className="grid gap-2">
      <h3 className="text-sm font-medium">منابع رسمی</h3>
      {sources.map((source) => (
        <Card className="elevation-source-card gap-3 py-4" key={source.id}>
          <CardHeader className="gap-2 px-4">
            <div className="flex items-start justify-between gap-3">
              <CardTitle className="text-sm leading-6">{source.title}</CardTitle>
              <Badge variant="secondary">مستندات لیارا</Badge>
            </div>
            {source.section ? (
              <p className="text-xs text-muted-foreground">{source.section}</p>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-2 px-4">
            {source.snippet ? (
              <p className="line-clamp-3 text-xs leading-6 text-muted-foreground">
                {source.snippet}
              </p>
            ) : null}
            <a
              className="flex min-w-0 items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              href={source.url}
              rel="noreferrer"
              target="_blank"
            >
              <span className="truncate" dir="ltr">
                {source.url}
              </span>
              <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
            </a>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}
