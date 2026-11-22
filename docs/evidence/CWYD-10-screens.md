# CWYD-10 — Design system and UI components

Card: [CWYD-10](https://goncalvesmarques.atlassian.net/browse/CWYD-10). The five handoff screens
composed from the components with static data, captured from the dev-only preview page at the
handoff size (1440 px wide, device scale 2).

```bash
cd frontend && npm run dev          # then open http://localhost:5173/preview.html#<screen>
npm run tokens:audit                # missing: 0, drift: 0, hardcoded: 0
```

| Handoff screen | Preview URL | Screenshot |
|---|---|---|
| 1 · Empty collection | `/preview.html#empty-collection` | [1-empty-collection.png](CWYD-10/1-empty-collection.png) |
| 2 · Indexing | `/preview.html#indexing` | [2-indexing.png](CWYD-10/2-indexing.png) |
| 3 · Answer with two sources | `/preview.html#answer-two-sources` | [3-answer-two-sources.png](CWYD-10/3-answer-two-sources.png) |
| 4 · Not enough evidence | `/preview.html#not-enough-evidence` | [4-not-enough-evidence.png](CWYD-10/4-not-enough-evidence.png) |
| 5 · Component states | `/preview.html#component-states` | [5-component-states.png](CWYD-10/5-component-states.png) |

## Token audit

`docs/design-tokens.json` measures 24 colors, 9 font sizes, 10 radii and 5 line heights in the
handoff. Near-duplicates were merged into one primitive each: colors `#EDEDEA` → `#F0F0EE`,
`#DCDCD7` → `#E4E4E0`, `#6B6B72` → `#5F5F66`; radii 3px → 4px, 5px → 6px; line heights 1.55 and
1.65 → 1.6. The brand symbol adds one color (`#C9D6F7`).

## Intentional differences from the PNGs

- **Formats copy (DOM-16).** "PDF files with selectable text" reads ".pdf with selectable text,
  .md or .txt"; failure and rejection messages are the backend's own (DOM-01, DOM-03).
- **No "Queued" status.** The backend has Indexing, Ready and Failed only (DOM-02).
- **No "Supports: …" label on source cards.** The API returns no such field.
- **"Show full passage"** appears only for passages longer than 200 characters (the API returns
  the full chunk; shorter passages are shown whole).
- **Line height.** Text without an explicit line height uses 1.5 (the handoff falls back to the
  browser's `normal`, about 1.2), so headers sit a few pixels lower.
- **Component states sheet.** Cards there are the real components, so "Not enough evidence" uses
  the full card instead of the sheet's smaller summary.
