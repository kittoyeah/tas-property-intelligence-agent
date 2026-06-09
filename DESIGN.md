# CanIBuild Design System

Grounded in the [Tasmanian Government Corporate Colour Standard](https://www.tas.gov.au/communications/identity/corporate-brand-identity-elements/corporate-colour).  
Token source: `frontend/src/styles/tokens.css`

---

## Colour

### Brand
| Token | Hex | Usage |
|---|---|---|
| `--sc-brand` | `#005A96` | Primary — Tas Govt official blue. Buttons, links, active states, header |
| `--sc-brand-hover` | `#004A7F` | Hover state on brand elements |
| `--sc-brand-active` | `#003A63` | Active / pressed state |
| `--sc-brand-tint` | `#E8F3FB` | Light brand background — chips, tag fills, subtle highlights |
| `--sc-brand-dark` | `#002C4E` | Header bar, footer background |

### CTA
| Token | Hex | Usage |
|---|---|---|
| `--sc-cta` | `#D9600A` | Primary action button (submit, download). Tasmanian earth ochre. |
| `--sc-cta-hover` | `#B84D07` | Hover state |
| `--sc-cta-tint` | `#FEF0E6` | Light CTA background |

### Surface & Layout
| Token | Hex | Usage |
|---|---|---|
| `--sc-bg` | `#F4F6F9` | Page background |
| `--sc-surface` | `#FFFFFF` | Cards, modals, dropdowns |
| `--sc-border` | `#DDE3EA` | Default border |
| `--sc-border-strong` | `#B0BEC9` | Dividers, focused inputs |

### Text
| Token | Hex | Usage |
|---|---|---|
| `--sc-text` | `#0D1B2A` | Body text — near-black |
| `--sc-text-soft` | `#445566` | Secondary labels, subheadings |
| `--sc-text-muted` | `#7A8FA0` | Placeholder, captions, metadata |
| `--sc-text-inverse` | `#FFFFFF` | Text on dark/brand backgrounds |

### Status
| Token | Hex | When to use |
|---|---|---|
| `--sc-hazard` | `#C0392B` | Flood, bushfire, landslip overlays |
| `--sc-hazard-tint` | `#FDECEA` | Hazard card background |
| `--sc-hazard-border` | `#F5C6C2` | Hazard card border |
| `--sc-heritage` | `#8A5C00` | Heritage / historic overlays |
| `--sc-heritage-tint` | `#FEF8E7` | Heritage card background |
| `--sc-heritage-border` | `#F0D080` | Heritage card border |
| `--sc-clear` | `#1E6E3C` | No overlays / safe result |
| `--sc-clear-tint` | `#EDFAF2` | Clear card background |
| `--sc-clear-border` | `#A3D9B8` | Clear card border |
| `--sc-info` | `#005A96` | Zone info, general overlay (reuses brand) |
| `--sc-info-tint` | `#E8F3FB` | Info card background |
| `--sc-info-border` | `#9AC5E8` | Info card border |

### Focus
| Token | Value | Usage |
|---|---|---|
| `--sc-focus` | `#005A96` | 3px solid focus ring — all interactive elements |
| `--sc-focus-offset` | `2px` | `outline-offset` |

**Rule:** Never use colour alone to convey status — always pair with an icon or label. All text on coloured backgrounds must meet WCAG AA (4.5:1 body, 3:1 large text).

---

## Tailwind Mapping

Tokens are exposed to Tailwind v4 via `@theme` in `globals.css`:

| Tailwind class | Maps to |
|---|---|
| `bg-brand-primary` / `text-brand-primary` | `--sc-brand` |
| `bg-brand-hover` | `--sc-brand-hover` |
| `bg-brand-tint` | `--sc-brand-tint` |
| `bg-brand-secondary` | `--sc-brand-dark` |
| `bg-cta` / `text-cta` | `--sc-cta` |
| `bg-cta-hover` | `--sc-cta-hover` |
| `bg-accent-red` / `text-accent-red` | `--sc-hazard` |
| `bg-accent-heritage` | `--sc-heritage` |
| `bg-accent-clear` | `--sc-clear` |

---

## Typography

Font: **Montserrat** (loaded via `next/font`).  
Scale follows Tailwind defaults — no custom sizes unless there's a real need.

| Role | Class | Weight |
|---|---|---|
| Page heading | `text-2xl` / `text-3xl` | `font-bold` (700) |
| Section heading | `text-sm` + `uppercase tracking-wider` | `font-bold` |
| Body | `text-sm` | `font-normal` (400) |
| Caption / meta | `text-xs` or `text-[10px]` | `font-medium` |
| Mono / clause ref | `font-mono text-[10px]` | `font-bold` |

---

## Component Conventions

### Cards
Use `.planbuild-card` for the main input form (inset brand-colour outline).  
All other cards: `bg-white border border-slate-200 rounded-xl shadow-sm`.

### Overlay chips
| Overlay type | Classes |
|---|---|
| Hazard (flood/fire/landslip) | `bg-[--sc-hazard-tint] text-[--sc-hazard] border-[--sc-hazard-border]` |
| Heritage | `bg-[--sc-heritage-tint] text-[--sc-heritage] border-[--sc-heritage-border]` |
| Zone / info | `bg-brand-tint text-brand-primary border-[--sc-info-border]` |
| Clear | `bg-[--sc-clear-tint] text-[--sc-clear] border-[--sc-clear-border]` |

### Buttons
- **Primary action** (submit, download): `bg-brand-primary hover:bg-brand-hover text-white`
- **CTA** (call-to-action where higher visual weight needed): `bg-cta hover:bg-cta-hover text-white`
- **Ghost / inline**: `bg-brand-tint hover:bg-brand-primary/20 text-brand-primary`
- **Disabled**: `bg-slate-200 text-slate-400 cursor-not-allowed`

### Focus rings
All interactive elements: `focus-visible:outline-3 focus-visible:outline-[--sc-focus] focus-visible:outline-offset-2`  
Inputs use `.planbuild-input` class.

### Blockquotes
- Warning / heritage: `.planbuild-blockquote`
- Hazard: `.planbuild-hazard-blockquote`
