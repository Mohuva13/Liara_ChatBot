---
name: liara-material-ui
description: Design or review the Liara assistant UI using Material Design 3 principles, Liara brand cues, Persian RTL behavior, adaptive layouts, and accessible interaction states. Use for chat-page, popup-widget, landing-state, responsive, theming, or UX work; do not use for backend-only tasks.
---

# Liara Material UI

Create a calm, technical, trustworthy Persian support experience. Material Design 3 is the design rationale; shadcn/ui remains the implementation layer.

## Workflow

1. Read `references/design-system.md` before making visual or interaction changes.
2. Inspect the existing design tokens and components before adding new ones.
3. Design the compact popup and full chat page as two surfaces over the same conversation model.
4. Specify all states: initial, focused, submitted, streaming, ready, empty retrieval, support escalation, offline, rate-limited, and fatal error.
5. Verify keyboard use, visible focus, screen-reader labels, contrast, reduced motion, zoom to 200%, and RTL/LTR mixed content.
6. Verify compact, medium, and expanded layouts with real Persian text, long URLs, tables, and code blocks.

## Invariants

- Set the document language to Persian and direction to RTL. Isolate code, commands, URLs, hashes, IDs, and technical tokens with `dir="ltr"` where needed.
- Preserve Liara's recognizable blue accent, neutral surfaces, and restrained visual density. Expressiveness must never obscure technical content.
- Use semantic design tokens; do not scatter raw color, radius, shadow, spacing, or z-index values through components.
- Never ship a blank initial chat. Provide a concise value proposition, topic starters grounded in Liara documentation, and a clear support boundary.
- The popup must not cover essential site controls, must preserve focus correctly, and must be dismissible with Escape.
- Source cards are first-class content and appear separately from the answer.
- Code blocks show a language label and an accessible Copy action; long lines scroll horizontally without breaking the page.
- Do not communicate state by color alone. Pair color with text, iconography, or shape.
- Animation is short and purposeful; honor `prefers-reduced-motion`.

## Output

For design work, report the affected surface, viewport states, reused/new tokens, accessibility checks, and screenshots or browser-test evidence. Do not call a UI complete based only on a desktop happy path.
