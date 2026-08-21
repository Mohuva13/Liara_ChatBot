"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  type ThemePreference,
  useTheme,
} from "@/features/theme/theme-provider";
import { Check, Laptop, Moon, Sun } from "lucide-react";

const THEMES: Array<{
  icon: typeof Sun;
  label: string;
  value: ThemePreference;
}> = [
  { icon: Laptop, label: "هماهنگ با سیستم", value: "system" },
  { icon: Sun, label: "روشن", value: "light" },
  { icon: Moon, label: "تیره", value: "dark" },
];

export function ThemeToggle() {
  const { mounted, resolvedTheme, setTheme, theme } = useTheme();
  const CurrentIcon = !mounted
    ? Laptop
    : theme === "system"
      ? Laptop
      : resolvedTheme === "dark"
        ? Moon
        : Sun;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            aria-label="انتخاب پوسته"
            className="transition-transform duration-150 active:scale-90"
            size="icon-sm"
            title="پوسته نمایش"
            type="button"
            variant="ghost"
          />
        }
      >
        <CurrentIcon
          aria-hidden="true"
          className="animate-in fade-in-0 zoom-in-75"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-44" dir="rtl">
        <DropdownMenuGroup>
          <DropdownMenuLabel>پوسته نمایش</DropdownMenuLabel>
          {THEMES.map(({ icon: Icon, label, value }) => (
            <DropdownMenuItem
              className="min-h-9 cursor-pointer"
              key={value}
              onClick={() => setTheme(value)}
            >
              <Icon aria-hidden="true" />
              <span>{label}</span>
              {theme === value ? (
                <Check aria-hidden="true" className="ms-auto text-primary" />
              ) : null}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
