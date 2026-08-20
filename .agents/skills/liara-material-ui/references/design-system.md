# Liara assistant design system

## Sources and intent

Use these sources as design evidence, not as component libraries:

- Material Design 3 overview: <https://m3.material.io/>
- Material adaptive canonical layouts: <https://m3.material.io/foundations/layout/canonical-examples/overview>
- Material interaction states: <https://m3.material.io/foundations/interaction/states/overview>
- Existing Liara documentation UI: `/home/mohuva/Desktop/hackaton/docs/src/components` and `/home/mohuva/Desktop/hackaton/docs/src/styles`

The current docs UI uses Liara blue (`#2196f3`) for active navigation and links, near-white surfaces, subtle borders, and dark neutral surfaces. Treat those values as brand evidence, then expose them through semantic tokens rather than copying raw values into JSX.

## Required semantic token families

- Color: `background`, `surface`, `surface-container`, `foreground`, `muted`, `border`, `primary`, `primary-foreground`, `info`, `success`, `warning`, `destructive`, `focus-ring`.
- Shape: `radius-control`, `radius-card`, `radius-popup`, `radius-code`.
- Elevation: `elevation-popup`, `elevation-floating-action`, `elevation-source-card`.
- Motion: `duration-fast`, `duration-standard`, `easing-standard`.
- Layout: `chat-content-max`, `popup-inline-size`, `popup-block-size`, `composer-max`, safe-area insets.

Support light and dark themes. Check WCAG contrast instead of assuming a Material or Liara color is accessible in every pairing.

## Adaptive layouts

Use behavior rather than device labels as the breakpoint criterion:

- Compact: popup becomes nearly full-width with safe-area spacing; chat page uses one pane; composer is sticky; source cards stack.
- Medium: popup retains a bounded floating surface; full page uses a centered primary pane and may reveal a compact contextual header.
- Expanded: full page may use a supporting pane for session information or sources, while the conversation remains the primary two-thirds region. Do not add a secondary pane without useful content.

Test at minimum 320, 375, 768, 1024, and 1440 CSS pixels, portrait and landscape where relevant.

## Chat surfaces

### Initial state

- Liara identity and a one-sentence scope statement.
- Three to five real topic starters such as deployment, databases, domains, logs, or AI service.
- A short boundary: answers come from official Liara documentation; uncertain cases lead to support.
- No fabricated recent activity, users, counters, or testimonials.

### Conversation state

- User and assistant roles must be distinguishable without oversized bubbles.
- Technical answer content gets the widest readable measure.
- Streaming has a stable layout, Stop action, and screen-reader announcement without excessive live-region chatter.
- Follow-up suggestions are actions, not claims. They must reflect the current answer and retrieved evidence.

### Source state

- Show source title, canonical docs URL, section heading when available, and a short excerpt only when it helps orientation.
- Open external links safely and preserve meaningful link text.
- Clearly distinguish official docs links from support/ticket links.

### Escalation state

- Explain that a reliable answer was not found or that prior steps failed repeatedly.
- Offer the official ticket path as a clear primary action.
- Preserve a copyable troubleshooting summary so the user can attach it to a ticket.

## Bidirectional text

- Entire shell: `lang="fa" dir="rtl"`.
- Code, terminal commands, JSON/YAML, URLs, email, identifiers, paths, versions, and keyboard shortcuts: isolated LTR containers.
- Do not reverse icon semantics: forward/back navigation follows the actual UI direction, while play, copy, external-link, and code icons keep their universal meaning.
- Use CSS logical properties (`margin-inline`, `padding-inline`, `inset-inline`) rather than left/right when possible.

## Accessibility gates

- Full keyboard path for launcher, popup, messages, sources, composer, Copy, Stop, retry, and close.
- Focus returns to the launcher after popup close.
- Dialog semantics for modal behavior, or a non-modal complementary region if page interaction must remain available; choose deliberately.
- Minimum comfortable touch targets and no hover-only information.
- Errors associated with the composer; rate-limit and network errors announced politely.
- Code Copy feedback is conveyed to assistive technology.
- `prefers-reduced-motion` disables nonessential transitions.
