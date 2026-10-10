# ZeroTrace AI Notes — Landing Page

Applied direction (overrides MASTER.md defaults where noted):

- **Pattern:** Product Demo + Features — Hero > App mockup (center) > Feature breakdown > CTA.
- **Style:** Dark OLED + flat hybrid. Deep near-black background `#08080c`, cards `#12141b`, border `#1e2130`. No hard shadows — 1px borders + subtle glows.
- **Color:** Brand violet `#7c5cff` (CTA/accents, matches the app). Emphasized violet `#8f70ff`. Text: foreground `#f4f5f7`, secondary `#9aa1b2`, muted `#6b7280`. Status accents only inside visuals: emerald `#22c55e`, amber `#f59e0b`, sky `#38bdf8`.
- **Typography:** Headings **Space Grotesk** (600/700, tight tracking). Body **DM Sans**. Monospace **JetBrains Mono** for badges, labels, code hints.
- **Motion:** Subtle IntersectionObserver reveal (translate-y + opacity, 500ms), hover 150-200ms. Respect `prefers-reduced-motion` (disable all).
- **Sections:** Sticky nav → Hero + mockup → Highlight band (AI) → 6-card feature grid → Developer strip (SQLite / REST API / MIT) → CTA card → Footer.

## Checklist
- [ ] No emojis as icons (inline SVG only)
- [ ] cursor-pointer on clickable, hover + focus states
- [ ] text contrast ≥ 4.5:1 (muted text only for non-essential)
- [ ] prefers-reduced-motion respected
- [ ] Responsive 375 / 768 / 1024 / 1440