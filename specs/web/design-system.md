# Design system · Tinta

**Status:** implemented · The visual contract of the web app (S14, S15). It is not a capability of its own:
S14 implements it in its first phase, and every screen of S14 and S15 uses it.

Reference mockups: the *Daily Trends · Diseño web* canvas
(https://claude.ai/artifact/R9vRSxFy6Xz18oy31Go8PF), with the front page, browse, detail, mobile
in dark mode, login, the CMS list, the edit form and this system. The canvas shows sample headlines;
the rules below win when they disagree with it.

## Direction
Editorial and minimal. Newspaper typography for headlines, a neutral and quiet interface, thin rules
instead of boxes, and a single accent color. There are no images: hierarchy comes from type, space
and rules. The reader feels like a front page; the CMS feels like a calm tool with the same voice.

Not part of the look: gradients, glass, drop shadows on content (only dialogs have one), colored card
backgrounds, emoji, icon-heavy chrome.

## Tokens
Defined once as CSS custom properties and exposed to Tailwind as theme colors (`bg-paper`,
`text-ink`, `border-rule`…). Components never use raw hex values.

### Color
| Token | Light | Dark | Use |
|---|---|---|---|
| `paper` | `#FBFBFA` | `#0E0E10` | Reader background |
| `surface` | `#FFFFFF` | `#17171A` | Cards, fields, tables, dialogs |
| `canvas` | `#F4F4F5` | `#121214` | CMS background |
| `ink` | `#111113` | `#EDEDEF` | Text, primary button, strong rules |
| `ink-soft` | `#3F3F46` | `#C4C4CC` | Descriptions and lead-ins |
| `meta` | `#5C5C66` | `#A1A1AA` | Dates, authors, help text |
| `rule` | `#E4E4E7` | `#26262B` | Separators and borders |
| `field-border` | `#D4D4D8` | `#3F3F46` | Inputs, secondary buttons, chips |
| `accent` | `#C2361F` | `#FF6B52` | Links, focus ring, active navigation |
| `danger` | `#A3301B` | `#FF7A66` | Destructive actions |
| `success-bg` / `success-fg` | `#EEF7F0` / `#1E5E2C` | `#13261A` / `#8FD19E` | Success notices |
| `error-bg` / `error-fg` | `#FDF1EF` / `#8A2414` | `#2A1512` / `#FFB4A6` | Error notices |

- Every text color passes WCAG AA (4.5:1) on the backgrounds it is used on, in both themes. A token
  pair that fails is a defect.
- The theme follows `prefers-color-scheme`; there is no manual switch (S14).

### Category colors
Each category has a color used **only** for an 8 px square marker next to its label. The label itself
is always `ink`, so color is never the only cue.

| Category | Label | Light | Dark |
|---|---|---|---|
| `POLITICS` | Política | `#3A5BA0` | `#7F9BE0` |
| `INTERNATIONAL` | Internacional | `#2F7F7A` | `#4FB3AC` |
| `ECONOMY` | Economía | `#A0702A` | `#D9A04A` |
| `SOCIETY` | Sociedad | `#7A4FA0` | `#B48AD9` |
| `SPORTS` | Deportes | `#2E8540` | `#5DBB6E` |
| `CULTURE` | Cultura | `#B0476B` | `#E07FA0` |
| `TECHNOLOGY` | Tecnología | `#3E5BC2` | `#7D94F0` |
| `SCIENCE` | Ciencia | `#1F7AA8` | `#5DB0DC` |
| `HEALTH` | Salud | `#B04A3A` | `#E58A7A` |
| `OPINION` | Opinión | `#52525B` | `#A1A1AA` |
| `OTHER` | Otros | `#8A8A94` | `#71717A` |

### Sources
Newspapers are shown by name in the serif face: *El Mundo*, *El Español*, *El Confidencial*,
*La Razón*, *La Vanguardia*, and *Redacción* for `CMS` (*El País* for stored `EL_PAIS` feeds). No
logos: they are trademarks of the newspapers.

### Typography
- **Newsreader** (variable, optical size) for headlines, lead-ins and newspaper names; **Inter**
  (variable) for the interface, body text, metadata and forms. Both are open-source (OFL) and
  self-hosted through `@fontsource-variable` packages: the app makes no request to Google Fonts.
- Fallbacks: `Georgia, serif` and `system-ui, sans-serif`.

| Style | Face | Size / line height | Use |
|---|---|---|---|
| Masthead | Newsreader 500, tracking −0.025em | 64 / 1.0 (40 on mobile) | Brand on the front page |
| Display | Newsreader 500, −0.02em | 46–56 / 1.05 (30 on mobile) | Lead story, detail headline |
| Title 1 | Newsreader 500, −0.015em | 36–48 / 1.1 | Page titles |
| Title 2 | Newsreader 500 | 21–24 / 1.2 | Card and list headlines |
| Lead-in | Newsreader 400 | 18–23 / 1.5 | Prominent descriptions |
| Body | Inter 400 | 15 / 1.5 (14 in the CMS) | General text |
| Meta | Inter 400 | 13 / 1.4 | Source, author, time |
| Label | Inter 600, uppercase, +0.1em | 11 / 1.2 | Categories, section labels |

### Space, shape and motion
- Spacing on a 4 px base: 4, 8, 12, 16, 24, 32, 40, 56, 80.
- Radius: 8 px for fields, 12 px for cards and panels, 16 px for dialogs, full (pill) for buttons and
  chips.
- Layout: content up to 1200 px with 32 px gutters (16 px below 640 px); reading width 760 px for the
  detail page; the CMS has a 240 px side menu that stacks above the content on narrow screens.
- Rules: 1 px `ink` above the main sections of the reader (masthead, *Más titulares*, footer), 1 px
  `rule` between items.
- Motion: 150–200 ms ease-out for hover, focus and appearing content; none when the system asks for
  reduced motion.

## Components
Built on shadcn/ui primitives restyled with the tokens, so behavior and accessibility come from the
primitives (Radix) and the look from Tinta.

| Component | Rules |
|---|---|
| Button | Pill, 44 px high (40 px in dense CMS rows). Variants: primary (`ink` background, `surface` text), secondary (`surface`, `field-border`), destructive (`danger`), link (`accent`, no background). Icon-only buttons have an `aria-label` and a 36–44 px target. |
| Chip | Pill toggle, 40 px high, `aria-pressed`. Pressed: `ink` background; otherwise `surface` with `field-border`. |
| Category label | 8 px square marker + Label style. Optional link to the browse page filtered by that category. |
| Feed card | Category label, headline (Title 2, links to the detail), optional description (2 lines max on cards), meta line *Source · author · time*. Variants: lead (Display), side, grid, list row (with the time column), compact (mobile). |
| Source link | *Leer en <newspaper>* with an outward arrow icon, opens the original in a new tab. |
| Field | Label above, 44 px input, `field-border`, 8 px radius, error message below in `error-fg`. |
| Select | Native `select` styled like a field (best on mobile and for accessibility). |
| Notice | Success or error, 8 px radius, `role="status"` or `role="alert"`. Transient confirmations are toasts at the bottom; errors that block a form stay inline. |
| Dialog | Confirmation only (delete). 16 px radius, the one shadow in the system, focus trapped, Escape closes. |
| Skeleton | `rule`-tinted bars shaped like the content they replace; no spinners for page content. |
| Empty state | A short serif sentence and one action; no illustration. |

## Icons
Lucide icons (stroke 2, 16–20 px), only where they carry meaning: search, external link, add,
refresh, edit, delete, menu, check, alert. Never decorative.

## Copy
- Spanish, sentence case, short. Buttons say what they do: *Guardar cambios*, *Cargar más*,
  *Actualizar portadas*.
- Times are relative when recent (*hace 2 h*) and absolute after a day (*20 oct*), with the full
  date and time in the `<time datetime>` element (S14).
- No exclamation marks or jokes in errors: say what happened and what the user can do.

## Acceptance criteria
- The tokens exist once (CSS custom properties plus the Tailwind theme) with both themes, and a unit
  test checks that every text/background pair listed above passes 4.5:1.
- The category and source mappings live in one module and are covered by tests (S14).
- Fonts load from the app bundle; a build makes no request to an external font host.
- Each component of the table exists in `src/components` with a test of its accessible role and
  states, and is used by the screens instead of ad-hoc markup.
- The screens of S14 and S15 match the canvas in layout and hierarchy at 1440 px and 390 px.
