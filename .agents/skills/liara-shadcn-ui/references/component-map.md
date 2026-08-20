# Component map and install order

Official references:

- Next.js installation: <https://ui.shadcn.com/docs/installation/next>
- CLI: <https://ui.shadcn.com/docs/cli>
- RTL for Next.js: <https://ui.shadcn.com/docs/rtl/next>

## Baseline inspection

Confirm these before installation:

- One package manager and one lockfile.
- Next.js App Router, TypeScript, React, Tailwind, `@/*` alias, and `src/` choice.
- `components.json` paths agree with `tsconfig.json`.
- `rtl: true`, `<html lang="fa" dir="rtl">`, and a direction provider where required.
- Dark mode strategy and semantic CSS variables exist before broad component customization.

## Minimal application primitives

Add primitives only when a feature needs them. The likely initial set is:

- `button`, `textarea`, `card`, `badge`, `separator`, `scroll-area`
- `tooltip`, `collapsible`, `dialog`, `sheet`
- `dropdown-menu` only if a real action menu exists
- `sonner` or the established toast system for Copy/error feedback

Do not preinstall a catalog. Smaller source ownership reduces maintenance and bundle cost.

## Composition map

| Product need | Primitive/composition | Notes |
|---|---|---|
| Popup launcher | Button + Tooltip | Fixed, safe-area aware, descriptive accessible name |
| Popup surface | non-modal region or Dialog | Choose semantics based on whether background remains interactive |
| Mobile popup | Sheet or full-screen Dialog | Preserve conversation state across layout changes |
| Welcome topic | Card/Button composition | Must send a real grounded prompt |
| Source card | Card + Badge + link | Separate from answer; canonical docs URL |
| Support escalation | Alert/Card + Button/link | Official ticket route only |
| Copy feedback | Button + toast/live text | Visible and announced |
| Status details | Collapsible | Never expose hidden chain-of-thought |

## CLI discipline

Use commands like:

```bash
pnpm dlx shadcn@latest add button textarea card badge separator scroll-area tooltip collapsible dialog sheet
```

Split the command if diff review is easier. After each batch:

1. Review `components.json`, CSS, dependencies, and generated code.
2. Resolve direction and token issues without forking upstream structure unnecessarily.
3. Run formatter, lint, type-check, focused tests, and production build.
4. Commit a coherent verified slice.
