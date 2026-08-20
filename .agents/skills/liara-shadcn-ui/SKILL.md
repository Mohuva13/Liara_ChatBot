---
name: liara-shadcn-ui
description: Initialize, add, customize, or review shadcn/ui components for the Liara Next.js frontend, including RTL configuration, semantic tokens, accessibility, and local component ownership. Use for component-library and frontend implementation tasks; do not use for visual direction without implementation or for backend code.
---

# Liara shadcn/ui

Use shadcn/ui as source-owned component code. Keep generated components close to upstream and put Liara-specific composition in feature components.

## Before running a CLI

1. Inspect `package.json`, lockfiles, `components.json`, Tailwind version, import aliases, React/Next versions, and existing component paths.
2. Use the repository's established package manager. Do not create a second lockfile.
3. Read `references/component-map.md` and install only components required by the current slice.
4. Check the current official CLI documentation before relying on remembered flags.

## Initialization

For the planned Persian Next.js application, initialize RTL explicitly when the project is ready:

```bash
pnpm dlx shadcn@latest init --rtl
```

If the project already has `components.json`, do not reinitialize blindly. Inspect and update it deliberately. Never use `--force` without reviewing the diff and obtaining authorization for overwritten files.

## Component rules

- Generated primitives live under the configured `components/ui` path.
- AI-specific generated components live under `components/ai-elements`.
- Feature composition lives under `features/chat`, `features/sources`, or the established equivalent.
- Put theme choices in CSS variables and Tailwind tokens, not per-instance class strings.
- Prefer CSS logical properties and shadcn's RTL support. Verify portal content such as tooltips, dropdowns, sheets, and dialogs inherits direction.
- Do not edit a primitive merely to satisfy one screen if composition or a wrapper will work.
- Keep component APIs typed. Avoid `any`, duplicated variants, and inaccessible icon-only controls.
- CLI output is a starting point: inspect every generated dependency and file, then run lint, type-check, unit tests, and a production build.

## Completion evidence

Report the exact CLI commands, generated/changed files, diff review, direction/theme verification, and checks run. A successful CLI exit alone is not completion.
