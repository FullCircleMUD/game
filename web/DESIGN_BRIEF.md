# FCM Website Design Brief

## Target Audience

Three overlapping groups, in order of priority:

1. **Old-school MUD players** — Grew up on CircleMUD, DikuMUD, ROM, SMAUG. They know what a MUD is and don't need convincing on the format. They care about depth, systems, and that feeling of being 16 and logged in at midnight. They're suspicious of anything that looks like marketing. Authenticity wins.

2. **Play-to-earn / blockchain gamers** — They've seen a hundred "revolutionary GameFi" projects. Most were scams. They can smell one instantly. They want to see a real game, not a tokenomics diagram. Contract addresses, not promises. Gameplay, not yield projections.

3. **XRPL community** — Curious about what's being built on the ledger. Technically literate, likely developers or early adopters. They'll check the ledger. They want to see competent integration, not hype.

**What all three share:** A low tolerance for bullshit, an appreciation for substance over style, and the ability to tell when something is real.

---

## Design Philosophy

**Game first, ledger second.** The website should feel like a game world, not a DeFi dashboard. The blockchain integration is a feature, not the headline. Lead with the experience, the world, the depth of systems — and mention that everything you earn is real and yours.

**Terminal aesthetic, modern execution.** The visual language draws from CRT terminals and text interfaces — the world these players grew up in — but the execution is clean, accessible, and professional. This is nostalgia done well, not cosplay.

**Understated confidence.** No hype language. No countdowns. No "revolutionary" or "first ever." The game speaks for itself. The contracts are on-chain and verifiable. The economy is real and documented. State facts. Let people draw their own conclusions.

---

## Colour Palette

### Core Colours

| Role | Name | Hex | Usage |
|---|---|---|---|
| **Background** | Deep Dark | `#121212` | Page background, base surface |
| **Surface** | Elevated Dark | `#1E1E1E` | Cards, panels, elevated elements |
| **Surface Border** | Charcoal | `#2C2C2C` | Card borders, dividers, table rules |
| **Primary Text** | Soft White | `#E0E0E0` | Body text, paragraphs |
| **Heading Text** | Bright White | `#F0F0F0` | Headings, emphasis, card titles |
| **Secondary Text** | Muted Gray | `#9E9E9E` | Captions, timestamps, helper text |

### Accent Colours

| Role | Name | Hex | Usage |
|---|---|---|---|
| **Primary Accent** | Phosphor Green | `#00FF41` | Links on hover, focus rings, terminal UI, active states |
| **Soft Accent** | Sage Green | `#7FFF7F` | Link text (default state), highlighted terms |
| **Secondary Accent** | Steel Blue | `#3D7A9E` | Buttons, badges, non-terminal interactive elements |
| **Gold** | Amber | `#DAA520` | Gold/currency references, premium indicators, warning states |
| **Danger** | Blood Red | `#CC4444` | Errors, destructive actions, combat damage |

### Accent Usage Rules

- **Green is the signature colour.** Use it for anything terminal-flavoured: links, command examples, interactive highlights, focus rings. It says "this is a text game" without a word of copy.
- **Blue is the workhorse.** Buttons, badges, navigation highlights. It provides contrast against the green without competing.
- **Gold is for value.** Use sparingly — gold coin references, premium content, economic indicators.
- **Never use green for body text.** Extended reading in green-on-dark is fatiguing. Reserve it for accents.

### Contrast Compliance (WCAG AA)

| Combination | Contrast Ratio | Passes |
|---|---|---|
| `#E0E0E0` on `#121212` | 15.3:1 | AA + AAA |
| `#F0F0F0` on `#121212` | 16.7:1 | AA + AAA |
| `#9E9E9E` on `#121212` | 7.4:1 | AA + AAA |
| `#7FFF7F` on `#121212` | 12.4:1 | AA + AAA |
| `#00FF41` on `#121212` | 11.8:1 | AA + AAA |
| `#3D7A9E` on `#121212` | 4.7:1 | AA (normal text) |
| `#DAA520` on `#121212` | 6.7:1 | AA + AAA |
| `#E0E0E0` on `#1E1E1E` | 12.9:1 | AA + AAA |

---

## Typography

### Font Stack

| Role | Font | Weight(s) | Source |
|---|---|---|---|
| **Headings** | Space Mono | 400, 700 | Google Fonts |
| **Body** | Space Grotesk | 400, 500, 600 | Google Fonts |
| **Terminal / Code** | Space Mono | 400 | Google Fonts |
| **Decorative (splash only)** | VT323 | 400 | Google Fonts |

**Why this pairing:** Space Mono and Space Grotesk are designed as siblings by Colophon Foundry — a monospace and proportional sans-serif from the same DNA. They harmonise naturally. Space Mono provides the terminal feel for headings and code; Space Grotesk is highly readable for body text.

VT323 is a pixel-perfect DEC VT320 terminal font. Use it only for decorative splash elements, ASCII art, or the site title. Never for body text.

### Font Loading

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&family=VT323&display=swap" rel="stylesheet">
```

### Type Scale

| Element | Font | Size | Weight | Line Height |
|---|---|---|---|---|
| Page title (h1) | Space Mono | 32px | 700 | 1.3 |
| Section heading (h2) | Space Mono | 24px | 700 | 1.3 |
| Subsection heading (h3) | Space Mono | 20px | 700 | 1.4 |
| Minor heading (h4/h5) | Space Mono | 18px | 400 | 1.4 |
| Body text | Space Grotesk | 16px | 400 | 1.6 |
| Lead text | Space Grotesk | 18px | 400 | 1.6 |
| Small / caption | Space Grotesk | 14px | 400 | 1.5 |
| Code / terminal | Space Mono | 14px | 400 | 1.5 |

### Paragraph Width

Maximum 75 characters per line for body text. On wide screens, constrain the content area rather than letting text span the full viewport.

---

## Layout

### Page Structure

```
┌─────────────────────────────────────────────────┐
│  NAVBAR (fixed top, dark, Space Mono links)     │
├─────────────────────────────────────────────────┤
│                                                 │
│  CONTENT AREA (max-width: 960px, centered)      │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Card / Section                           │  │
│  │  ─────────────────────                    │  │
│  │  Content in Space Grotesk body text       │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Card    │  │  Card    │  │  Card    │      │
│  │  Grid    │  │  Grid    │  │  Grid    │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                 │
├─────────────────────────────────────────────────┤
│  FOOTER (minimal, dark)                         │
└─────────────────────────────────────────────────┘
```

### Spacing

Use an 8px base unit:

| Token | Value | Usage |
|---|---|---|
| `xs` | 4px | Tight gaps, icon padding |
| `sm` | 8px | Inline element spacing |
| `md` | 16px | Standard element spacing |
| `lg` | 24px | Section padding, card body |
| `xl` | 32px | Between cards, major sections |
| `xxl` | 48px | Page top/bottom padding |

### Cards

- Background: `#1E1E1E`
- Border: 1px solid `#2C2C2C`
- Border radius: 4px (subtle, not rounded — the terminal aesthetic is angular)
- Padding: 24px
- Margin bottom: 16px between stacked cards
- No box shadow (flat design — shadows feel wrong against the terminal aesthetic)

### Responsive Breakpoints

Follow Bootstrap 4 defaults:

| Breakpoint | Width | Behaviour |
|---|---|---|
| xs | < 576px | Single column, stacked cards |
| sm | >= 576px | Still mostly single column |
| md | >= 768px | Two-column grids, navbar expands |
| lg | >= 992px | Three-column grids |
| xl | >= 1200px | Content area caps at max-width |

---

## Component Patterns

### Navigation Bar

- Dark background (`#0D1117`)
- Space Mono for link text
- Active link: phosphor green (`#00FF41`)
- Hover: soft green (`#7FFF7F`)
- No underlines — the green colour is sufficient affordance
- Logo area: game name in Space Mono, slogan in Space Grotesk italic

### Buttons

| Variant | Background | Text | Border | Hover |
|---|---|---|---|---|
| Primary | `#3D7A9E` | `#FFFFFF` | none | lighten 10% |
| Secondary | `#2C2C2C` | `#E0E0E0` | `#444444` | `#3C3C3C` |
| Outline | transparent | `#7FFF7F` | `#7FFF7F` | `#00FF41` bg, `#121212` text |
| Danger | `#CC4444` | `#FFFFFF` | none | lighten 10% |

Border radius: 4px. Padding: 8px 16px.

### Links

- Default: `#7FFF7F` (sage green)
- Hover: `#00FF41` (phosphor green)
- Visited: `#5FBF5F` (dimmer green)
- No underline by default; underline on hover

### Terminal Blocks

For command examples, code snippets, and terminal-style content:

```css
.terminal-block {
  background: #0A0A0A;
  border: 1px solid #333333;
  border-radius: 4px;
  padding: 16px;
  font-family: 'Space Mono', monospace;
  font-size: 14px;
  color: #00FF41;
  overflow-x: auto;
}
```

### Tables

- Header: `#1E1E1E` background, `#F0F0F0` text, Space Mono
- Rows: alternating `#121212` / `#181818`
- Borders: `#2C2C2C`
- Hover: `#222222`

---

## Imagery & Iconography

### No Stock Art

This is a text game. The visual identity comes from typography, colour, and layout — not from stock fantasy renders or AI-generated art. If imagery is used, it should be:

- **ASCII art** — authentic to the MUD genre
- **Terminal screenshots** — actual gameplay
- **Diagrams** — clean, flat, using the colour palette (economy flows, system diagrams)

### Icons

Use a minimal icon set (Font Awesome or Bootstrap Icons, both already available). Keep icons small and functional — navigation aids, not decoration. Prefer text labels over icon-only buttons.

---

## Dos and Don'ts

### Do

- Lead with the game experience, not the token
- Use terminal green as a signature accent
- Show actual gameplay (terminal output, command examples)
- State facts plainly — contract addresses, backing ratios, mechanics
- Keep copy concise and direct
- Make the site feel like it was built by someone who plays MUDs

### Don't

- Use hype language ("revolutionary", "first ever", "1000x")
- Show tokenomics diagrams on the landing page
- Use countdown timers or artificial urgency
- Add animation for animation's sake (subtle hover transitions are fine)
- Use rounded, bubbly, or "Web3 dashboard" aesthetics
- Put yield/ROI projections anywhere
- Use more than 2-3 colours in any single view

---

## Implementation Notes

### Bootstrap 4 Strategy

Evennia ships Bootstrap 4.x. Rather than fighting it, layer a custom CSS file on top:

1. Create `static/website/css/fcm-dark.css`
2. Load it after Bootstrap in `base.html`
3. Override body, card, navbar, form, table, and button colours
4. Add utility classes: `.bg-surface`, `.bg-elevated`, `.text-accent`, `.terminal-block`
5. Do not modify Bootstrap source (survives Evennia upgrades)

### CSS Custom Properties

Define the palette as CSS variables for consistency:

```css
:root {
  --fcm-bg: #121212;
  --fcm-surface: #1E1E1E;
  --fcm-border: #2C2C2C;
  --fcm-text: #E0E0E0;
  --fcm-text-bright: #F0F0F0;
  --fcm-text-muted: #9E9E9E;
  --fcm-green: #00FF41;
  --fcm-green-soft: #7FFF7F;
  --fcm-blue: #3D7A9E;
  --fcm-gold: #DAA520;
  --fcm-danger: #CC4444;
  --fcm-nav-bg: #0D1117;
  --fcm-font-heading: 'Space Mono', monospace;
  --fcm-font-body: 'Space Grotesk', sans-serif;
  --fcm-font-terminal: 'Space Mono', monospace;
}
```

### File Structure

```
web/
├── static/website/
│   ├── css/
│   │   └── fcm-dark.css          ← custom dark theme overrides
│   ├── fonts/                    ← (if self-hosting fonts later)
│   └── images/
│       └── fcm-logo.png          ← replace Evennia logo
├── templates/website/
│   ├── base.html                 ← override to add font links + CSS
│   ├── _menu.html                ← already customised
│   ├── homepage/
│   │   └── main-content.html     ← already customised
│   ├── vision.html
│   ├── about.html
│   ├── docs.html
│   ├── docs_gameplay.html
│   ├── docs_blockchain.html
│   ├── docs_client_api.html
│   └── markets.html
└── DESIGN_BRIEF.md               ← this file
```
