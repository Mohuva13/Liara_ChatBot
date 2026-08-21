"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { codeFilename } from "@/features/chat/components/code-block-utils";
import { cn } from "@/lib/utils";
import {
  Check,
  ClipboardCheck,
  Copy,
  Download,
  TriangleAlert,
} from "lucide-react";
import {
  type ComponentProps,
  isValidElement,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";
import { CodeBlock, useIsCodeFenceIncomplete } from "streamdown";

type ActionState = "idle" | "success" | "failed";

async function copyWithFallback(value: string): Promise<void> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
  } catch {
    // Some browsers expose Clipboard API but reject it outside the focused tab.
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) {
    throw new Error("copy failed");
  }
}

function downloadCode(value: string, language: string): void {
  const blob = new Blob([value], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = codeFilename(language);
  anchor.hidden = true;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function childrenText(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number") {
    return String(children);
  }
  if (Array.isArray(children)) {
    return children.map(childrenText).join("");
  }
  if (isValidElement<{ children?: ReactNode }>(children)) {
    return childrenText(children.props.children);
  }
  return "";
}

function CodeActions({
  code,
  language,
  disabled,
}: {
  code: string;
  language: string;
  disabled: boolean;
}) {
  const [copyState, setCopyState] = useState<ActionState>("idle");
  const [downloadState, setDownloadState] = useState<ActionState>("idle");
  const timers = useRef<number[]>([]);

  useEffect(
    () => () => {
      for (const timer of timers.current) {
        window.clearTimeout(timer);
      }
    },
    [],
  );

  const resetLater = (
    setter: (state: ActionState) => void,
    delay = 1800,
  ) => {
    timers.current.push(window.setTimeout(() => setter("idle"), delay));
  };

  const copy = async () => {
    try {
      await copyWithFallback(code);
      setCopyState("success");
    } catch {
      setCopyState("failed");
    }
    resetLater(setCopyState);
  };

  const download = () => {
    try {
      downloadCode(code, language);
      setDownloadState("success");
    } catch {
      setDownloadState("failed");
    }
    resetLater(setDownloadState);
  };

  const copyLabel =
    copyState === "success"
      ? "کد کپی شد"
      : copyState === "failed"
        ? "کپی کد ناموفق بود"
        : "کپی کد";
  const downloadLabel =
    downloadState === "success"
      ? "فایل کد دانلود شد"
      : downloadState === "failed"
        ? "دانلود کد ناموفق بود"
        : "دانلود کد";

  return (
    <div className="flex items-center gap-0.5" dir="rtl">
      <Tooltip>
        <TooltipTrigger
          aria-label={downloadLabel}
          className="grid size-8 cursor-pointer place-items-center rounded-md text-muted-foreground transition-[color,background-color,transform] duration-150 hover:bg-muted hover:text-foreground active:scale-90 disabled:cursor-not-allowed disabled:opacity-45"
          data-code-action="download"
          disabled={disabled}
          onClick={download}
          type="button"
        >
          {downloadState === "success" ? (
            <Check aria-hidden="true" className="size-4 animate-in zoom-in-75" />
          ) : downloadState === "failed" ? (
            <TriangleAlert
              aria-hidden="true"
              className="size-4 animate-in zoom-in-75 text-destructive"
            />
          ) : (
            <Download aria-hidden="true" className="size-4" />
          )}
        </TooltipTrigger>
        <TooltipContent>{downloadLabel}</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger
          aria-label={copyLabel}
          className="grid size-8 cursor-pointer place-items-center rounded-md text-muted-foreground transition-[color,background-color,transform] duration-150 hover:bg-muted hover:text-foreground active:scale-90 disabled:cursor-not-allowed disabled:opacity-45"
          data-code-action="copy"
          disabled={disabled}
          onClick={() => void copy()}
          type="button"
        >
          {copyState === "success" ? (
            <ClipboardCheck
              aria-hidden="true"
              className="size-4 animate-in zoom-in-75 text-primary"
            />
          ) : copyState === "failed" ? (
            <TriangleAlert
              aria-hidden="true"
              className="size-4 animate-in zoom-in-75 text-destructive"
            />
          ) : (
            <Copy aria-hidden="true" className="size-4" />
          )}
        </TooltipTrigger>
        <TooltipContent>{copyLabel}</TooltipContent>
      </Tooltip>
      <span aria-live="polite" className="sr-only">
        {copyState !== "idle" ? copyLabel : ""}
        {downloadState !== "idle" ? downloadLabel : ""}
      </span>
    </div>
  );
}

type MarkdownCodeProps = ComponentProps<"code"> & { node?: unknown };

export function MarkdownCode({
  children,
  className,
  node: _node,
  ...props
}: MarkdownCodeProps) {
  void _node;
  const isBlock = Object.prototype.hasOwnProperty.call(props, "data-block");
  const isIncomplete = useIsCodeFenceIncomplete();
  const code = childrenText(children).replace(/\n$/, "");
  const language = className?.match(/language-([\w#+.-]+)/)?.[1] ?? "text";

  if (!isBlock) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  }

  return (
    <CodeBlock
      className={cn("my-4", className)}
      code={code}
      isIncomplete={isIncomplete}
      language={language}
    >
      <CodeActions
        code={code}
        disabled={isIncomplete}
        language={language}
      />
    </CodeBlock>
  );
}
