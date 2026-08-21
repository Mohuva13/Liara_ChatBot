"use client";

import { useEffect, useRef, useState } from "react";
import { MessageCircle, X } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ChatShell } from "@/features/chat/components/chat-shell";

export function ChatPopup() {
  const [open, setOpen] = useState(false);
  const launcherRef = useRef<HTMLButtonElement>(null);

  const close = () => {
    setOpen(false);
    window.requestAnimationFrame(() => launcherRef.current?.focus());
  };

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      {open ? (
        <aside
          aria-label="پنجره دستیار مستندات لیارا"
          className="elevation-popup fixed inset-x-2 bottom-20 z-50 h-[min(42rem,calc(100dvh-6rem))] sm:inset-x-auto sm:start-4 sm:w-[var(--popup-inline-size)]"
          id="liara-assistant-popup"
        >
          <ChatShell onClose={close} surface="popup" />
        </aside>
      ) : null}

      <Tooltip>
        <TooltipTrigger
          aria-controls="liara-assistant-popup"
          aria-expanded={open}
          aria-label={open ? "بستن دستیار لیارا" : "باز کردن دستیار لیارا"}
          className="elevation-floating-action fixed start-4 bottom-4 z-50 grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground transition-transform hover:scale-105 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          onClick={() => (open ? close() : setOpen(true))}
          ref={launcherRef}
          type="button"
        >
          {open ? <X aria-hidden="true" /> : <MessageCircle aria-hidden="true" />}
        </TooltipTrigger>
        <TooltipContent>دستیار مستندات لیارا</TooltipContent>
      </Tooltip>
    </>
  );
}
