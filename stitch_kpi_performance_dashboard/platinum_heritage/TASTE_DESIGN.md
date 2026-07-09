# Design System: Platinum Heritage CRM

> Stitch-ready semantic design language for a high-end real-estate CRM.  
> Density **6** (Daily App Balanced → lightly dense ops UI) · Variance **5** (Offset Asymmetric, professional) · Motion **4** (Fluid CSS, restrained) · Creativity **7**.

---

## 1. Visual Theme & Atmosphere

A **quiet luxury gallery** for property professionals — sophisticated, trustworthy, and timeless. The interface behaves like a well-lit architecture studio: warm cream canvas, cool platinum structure, and a single deep-ink accent that never shouts.

The mood is **clinical yet warm**. Whitespace is intentional, not empty. Data density is comfortable for all-day use (pipeline boards, inventory grids, client cards) without sliding into cockpit chaos. Layouts prefer **left-aligned page heroes** and **asymmetric filter + content splits** over centered marketing compositions.

Elevation is tonal, not theatrical: pure white cards lift off cream with hairline platinum borders and a single soft, blue-tinted shadow reserved for hover. No neon, no purple, no glassmorphism.

**Brand personality:** Sophisticated · Trustworthy · Timeless · Gallery-minimal · Corporate restraint.

---

## 2. Color Palette & Roles

Maximum **one accent**. Saturation kept deliberately low. No purple/neon spectrum.

| Token name | Hex | Role |
|------------|-----|------|
| **Gallery Cream** | `#F4F2E5` | Primary app canvas / main content background — warm gallery floor |
| **Cool Mist** | `#F7F9FF` | Alternate soft surface (sidebar adjacency, tonal layers) |
| **Pure Surface** | `#FFFFFF` | Cards, modals, elevated panels |
| **Ink Navy** | `#142435` | Primary text, primary buttons, active nav — near-black with blue depth (never `#000000`) |
| **Deep Heritage** | `#2A3A4B` | Single accent / brand CTA fill, focus borders, score emphasis |
| **Dark Text Blue** | `#1B2631` | High-legibility body on cream when extra contrast is needed |
| **Muted Steel** | `#5D5E5F` | Secondary text, labels, metadata, helper copy |
| **Quiet Slate** | `#44474C` | On-surface variant — captions, table headers |
| **Platinum Line** | `#C0C0C0` | 1px structural borders, dividers, input outlines, secondary icons |
| **Whisper Outline** | `#C4C6CC` | Softer outline-variant for nested UI |
| **Surface Tint Low** | `#EDF4FF` | Hover rows, selected chips, soft highlight wells |
| **Surface Container** | `#E3EFFE` | Segmented controls, rationale boxes, soft chips |
| **Error Crimson** | `#BA1A1A` | Errors only — never as brand accent |
| **Error Wash** | `#FFDAD6` | Error container background |
| **Success Signal** | `#10B981` | Match score dots, positive status only (not a second brand accent) |

**Functional rules**
- Primary CTA = **Deep Heritage** (`#2A3A4B`) or **Ink Navy** (`#142435`) with white label
- Secondary CTA = white fill + **Platinum Line** border + Ink Navy text
- Focus ring = Deep Heritage, 1px border transition (no outer glow)
- Shadows tinted with Ink Navy at 6% opacity: `0 8px 30px rgba(27, 38, 49, 0.06)`
- Status colors (green/amber/red) are **semantic only**, never brand identity

---

## 3. Typography Rules

Dashboard = **sans only**. No serif anywhere in CRM chrome.

| Role | Font | Specs |
|------|------|--------|
| **Display / Page titles** | IBM Plex Sans | 28–32px · weight 600 · line-height 1.25 · letter-spacing −0.01em to −0.02em |
| **Section headlines** | IBM Plex Sans | 20–24px · weight 600 · tight tracking |
| **Body** | IBM Plex Sans | 16px · weight 400 · line-height 24px · max ~65ch for long copy |
| **Labels / Kickers** | IBM Plex Sans | 11–12px · weight 500 · uppercase · letter-spacing 0.08–0.12em · Muted Steel |
| **Mono / numbers** | IBM Plex Mono (or JetBrains Mono fallback) | Tabular nums for prices, scores, IDs, timestamps |

**Hierarchy principles**
- Weight and color carry hierarchy more than raw size
- Kickers above page titles (e.g. `PIPELINE`, `INVENTORY`, `RELATIONSHIPS`)
- Never scream display type on internal CRM screens

**Banned**
- Inter
- Generic system UI stacks as the only identity font
- Any serif (Georgia, Garamond, Times, etc.) in dashboards
- Gradient text on headers
- `LABEL // YEAR` typography tricks

---

## 4. Component Stylings

### Buttons
- **Primary:** Deep Heritage fill · white label · 8px radius · 12px 24px padding · 14px medium weight · slight letter-spacing  
  Active: translateY(1px) tactile press · opacity 0.92 on hover · **no outer glow**
- **Secondary:** Pure Surface · Platinum Line 1px · Ink Navy text · same radius/padding  
  Hover: Surface Tint Low background
- One primary CTA per page header. No dual “Learn more” pairs.

### Cards & Panels
- Pure Surface · Platinum Line 1px · radius **8–12px** (architectural, not pill-soft 2.5rem on data cards)
- Hover elevation only: `0 8px 30px rgba(27, 38, 49, 0.06)`
- Use cards when grouping a record (property, client, deal). For dense tables, prefer row dividers + hover wash instead of card-in-card nesting
- Property cards may use **8px** radius on media to echo modern architectural framing

### Inputs & Forms
- Label **above** field · 12px uppercase kicker style optional for filters
- Field: transparent or Cool Mist fill · Platinum Line border · 4–8px radius  
  Focus: border → Deep Heritage · no floating labels
- Error text **below** field in Error Crimson · Error Wash for block messages
- Gap: 8px base rhythm (linear 8px scale)

### Navigation
- Fixed or sticky sidebar on desktop · Pure Surface · Platinum right border
- Active item: Deep Heritage / Ink Navy solid fill · white label
- Inactive: Quiet Slate · hover Surface Tint Low
- Mobile: collapse to header + drawer · 44px min touch targets

### Chips & Status
- Small pills · 10–11px · Platinum or soft container fill · sparingly
- Match score pill: white · Platinum border · 8px green/amber/slate dot + “NN% Match”

### Loaders
- **Skeleton shimmer** matching card/row geometry — no generic centered circular spinners for page loads
- Shimmer uses Cool Mist → Surface Container sweep via opacity/transform only

### Empty States
- Composed: outline icon (Material Symbols) + one-line explanation + single primary action  
  Example: dashed Platinum well · `inbox` icon · “No deals in this stage” · optional “Add deal”
- Never emoji · never “Nothing here yet ✨”

### Data / Ops specifics (CRM)
- Kanban columns: light cream-on-white wells · always show all stages
- Tables: header row Surface Tint Low · uppercase label type · row hover wash
- Modals: centered · max-width ~32rem · Pure Surface · Platinum border · dimmed Ink Navy scrim at ~40%

---

## 5. Layout Principles

- **Max width:** 1280px content column centered inside app shell (sidebar + main)
- **Grid:** CSS Grid first · 12-column desktop · 24px gutters · 8px base spacing unit
- **Page header pattern:** Left block = kicker + title + subtitle · Right = single primary CTA (asymmetric split, not centered hero)
- **Main canvas:** Gallery Cream full height of content scroller (`min-height: 100%` of main · prefer `min-h-[100dvh]` only for full-bleed marketing surfaces)
- **No overlapping layers** of interactive content · modals are the only full-viewport overlays
- **Banned layout clichés:** centered marketing hero on CRM pages · equal “3 feature cards” promo rows · absolute-positioned text over photos for core UI chrome
- Inventory / clients: responsive card grids that collapse to **1 column** below 768px (2 → 1, not awkward 3-wide on phone)
- Pipeline: horizontal scroll of fixed-width columns is allowed on desktop boards; on mobile stack or horizontal scroll with clear affordance — **no accidental page-level horizontal overflow**

### Responsive
- **&lt; 768px:** single column · sidebar off-canvas · padding 16px · titles clamp down (e.g. `clamp(1.5rem, 4vw, 2rem)`)
- **Touch:** minimum 44×44px interactive targets
- **Body text:** minimum 14–16px
- **Section gaps:** `clamp(1.5rem, 4vw, 3rem)` between major blocks

---

## 6. Motion & Interaction

- **Default easing:** spring-like CSS — approximate `cubic-bezier(0.22, 1, 0.36, 1)` · avoid linear
- **Spring intent:** stiffness ~100 · damping ~20 (weighty, not bouncy toy)
- **What may move:** `transform`, `opacity` only
- **Hover cards:** 200–300ms shadow/opacity · optional `translateY(-2px)` max
- **Lists:** prefer short stagger (40–60ms) on first paint of card grids when JS is available; server-rendered lists may appear at once
- **Active dashboard micro-loops (sparingly):** soft pulse on unread notification badge · shimmer on skeletons · **no** perpetual floating blobs or typewriter on every label
- **Buttons:** active press = 1px downward translate · no custom cursors
- **Respect `prefers-reduced-motion`:** disable staggers and loops

---

## 7. Anti-Patterns (Banned)

**Never do these in Stitch generations or product UI:**

1. No emojis in UI chrome or empty states  
2. No **Inter** font  
3. No pure black `#000000`  
4. No neon / outer-glow shadows / purple “AI” gradients  
5. No oversaturated accent rainbows — **one** deep blue accent only  
6. No generic serif fonts in the CRM  
7. No centered marketing heroes on operational screens  
8. No “3 equal cards” feature marketing rows as default content layout  
9. No overlapping text-on-image for core navigation or forms  
10. No custom mouse cursors  
11. No AI copy clichés: *Elevate, Seamless, Unleash, Next-Gen, Revolutionary*  
12. No filler: “Scroll to explore”, bouncing chevrons, swipe arrows  
13. No `SYSTEM // 2024` or `METRICS // 2025` label formatting  
14. No fabricated metrics (“99.98% uptime”, “124ms response”) — use real data or `[metric]` placeholders  
15. No fake names (John Doe, Acme Corp, Nexus AI) in design comps when real sample data exists  
16. No broken Unsplash links — use local assets, `picsum.photos`, or solid tonal placeholders  
17. No glassmorphism stacks or multi-layer frosted panels  
18. No equal-weight dual primary CTAs competing in the same header  

---

## 8. Stitch Generation Notes

When prompting Stitch with this system:

- Product: **Platinum Heritage** real-estate CRM (inventory, clients, agents, deals pipeline, tasks, AI match / opportunities)
- Shell: left sidebar + cream main canvas + white elevated content
- Page headers always use **kicker + title + one primary action**
- Prefer Material Symbols Outlined for icons (weight 400, no filled candy icons)
- Persian/RTL content may appear in listings — keep LTR chrome; allow RTL in data fields
- Match score UI: pill with status dot + percent · rationale box in Surface Container with psychology icon
- SMS/outreach drawers: context chips for client phone + selected needs + multi-property lists

### Token quick-copy for prompts

```
Background: #F4F2E5 (Gallery Cream)
Surface: #FFFFFF
Primary text: #142435
Accent / CTA: #2A3A4B
Secondary text: #5D5E5F
Border: #C0C0C0
Font: IBM Plex Sans
Mono numbers: IBM Plex Mono
Radius: 8px cards, 4px inputs
Shadow: 0 8px 30px rgba(27,38,49,0.06)
```

---

## 9. Relationship to Existing Code

This DESIGN.md is the **semantic source of truth** for Stitch generation. Runtime tokens live in:

- `static/css/stitch.css` (`--brand-cream`, `--brand-deep-blue`, `--brand-platinum`, surface utilities)
- Tailwind PH config in `templates/base.html`
- Project: Stitch **KPI Performance Dashboard** · design system asset `assets/1dee9814aeab494b99629a9fe04852bd`

When Stitch and code diverge, prefer **this document + brand hexes** for new screens, then port tokens into `stitch.css`.
