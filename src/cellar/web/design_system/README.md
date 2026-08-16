# Cellar — Brand & Token Kit (Direction A · Clinical)

Paste-ready assets for the Cellar frontend.

## Files
- `cellar-mark.svg` — primary logo mark (cell + nucleus). Uses `currentColor`, so it takes the color of its CSS `color` property.
- `cellar-mark-favicon.svg` — heavier-weight mark for ≤24px / favicon use.
- `cellar-icon.svg` — app icon (green rounded square, reversed mark). Fixed colors.
- `tokens.css` — CSS custom properties + optional `.cellar-*` component classes.
- `tokens.json` — same values as data (for Tailwind config, JS themes, Style Dictionary, etc.).

## 1. Fonts
Add to your `<head>` (or import in CSS):
```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

## 2. Tokens
```css
@import "./cellar/tokens.css";

body { background: var(--cellar-paper); color: var(--cellar-ink); font-family: var(--cellar-font-body); }
```

## 3. Logo
```html
<!-- color it however you like -->
<span style="color: var(--cellar-xylem)">
  <img src="/cellar/cellar-mark.svg" width="28" height="28" alt="Cellar" />
</span>

<!-- inline the SVG instead to use currentColor from a parent -->
```
Primary color is **Xylem `#34573B`**; it reverses to **Sage/paper** on dark surfaces.

## 4. Tailwind (optional)
```js
// tailwind.config.js — pull straight from tokens.json
const t = require('./cellar/tokens.json');
module.exports = {
  theme: {
    extend: {
      colors: {
        paper: t.color.paper,
        surface: t.color.surface,
        ink: { DEFAULT: t.color.ink, muted: t.color.inkMuted, faint: t.color.inkFaint },
        xylem: t.color.brand.xylem,
        sage: t.color.brand.sage,
        signal: t.color.brand.signal,
      },
      fontFamily: {
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        body: ['Instrument Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      borderRadius: { sm: '7px', md: '11px', lg: '14px' },
    },
  },
};
```

## Conventions
- **Mono for data.** All measured values (mutations, dependency scores, counts, IDs) use IBM Plex Mono. Prose uses Instrument Sans; headings use Space Grotesk.
- **Model-type chips** each have a fixed color trio (`fg` / `tint` / `border`) — see `modelType` in the tokens.
- **Confidence** maps to a 3-step scale: strong ≥80%, moderate 50–79%, weak <50%.
