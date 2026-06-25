---
name: Platinum Heritage
colors:
  surface: '#f7f9ff'
  surface-dim: '#d0dbea'
  surface-bright: '#f7f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#edf4ff'
  surface-container: '#e3effe'
  surface-container-high: '#dee9f8'
  surface-container-highest: '#d8e4f3'
  on-surface: '#111d27'
  on-surface-variant: '#44474c'
  inverse-surface: '#26313d'
  inverse-on-surface: '#e8f2ff'
  outline: '#74777d'
  outline-variant: '#c4c6cc'
  surface-tint: '#506072'
  primary: '#142435'
  on-primary: '#ffffff'
  primary-container: '#2a3a4b'
  on-primary-container: '#93a4b8'
  inverse-primary: '#b7c8dd'
  secondary: '#5d5e5f'
  on-secondary: '#ffffff'
  secondary-container: '#e0dfdf'
  on-secondary-container: '#626363'
  tertiary: '#23241c'
  on-tertiary: '#ffffff'
  tertiary-container: '#393930'
  on-tertiary-container: '#a3a297'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d3e4fa'
  primary-fixed-dim: '#b7c8dd'
  on-primary-fixed: '#0c1d2d'
  on-primary-fixed-variant: '#38485a'
  secondary-fixed: '#e3e2e2'
  secondary-fixed-dim: '#c6c6c6'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#464747'
  tertiary-fixed: '#e5e3d6'
  tertiary-fixed-dim: '#c8c7bb'
  on-tertiary-fixed: '#1c1c14'
  on-tertiary-fixed-variant: '#47473e'
  background: '#f7f9ff'
  on-background: '#111d27'
  surface-variant: '#d8e4f3'
  surface-white: '#FFFFFF'
  error-red: '#BA1A1A'
typography:
  display-lg:
    fontFamily: IBM Plex Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: IBM Plex Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: IBM Plex Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: IBM Plex Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
  max-width: 1280px
---

## Brand & Style

The brand personality of this design system is **Sophisticated, Trustworthy, and Timeless**. Tailored for the high-end real estate market, the interface functions as a silent, premium gallery, allowing high-resolution property imagery to lead the experience.

The aesthetic follows a **Modern Minimalist** movement with **Corporate** undertones. It prioritizes clarity, structural alignment, and generous whitespace to evoke a sense of exclusivity. The emotional response is one of security and prestige, ensuring users feel they are engaging with an established, professional institution.

## Colors

The color palette is rooted in corporate stability and luxury materials. 

- **Deep Blue (#2A3A4B)**: The primary brand color, representing authority and stability. It is used for primary interactive elements and headers.
- **Platinum (#C0C0C0)**: A metallic secondary accent used for borders, dividers, and secondary icons to provide a high-end finish.
- **Cream (#F4F2E5)**: The primary background color. It provides warmth and a "gallery" feel, reducing the clinical harshness of pure white.
- **Dark Text Blue (#1B2631)**: The neutral color reserved for typography to ensure maximum legibility and contrast against the cream background.
- **Surface White (#FFFFFF)**: Used exclusively for card containers and modals to create a "lifted" appearance over the cream background.

## Typography

The system utilizes **IBM Plex Sans** to maintain a systematic, technical, and professional appearance. The hierarchy is strictly enforced to ensure complex property data remains digestible.

- **Headlines**: Set with tighter letter spacing and heavier weights to command attention and convey architectural precision.
- **Body Text**: Uses generous line heights to ensure readability during long browsing sessions.
- **Labels**: Utilize medium weights and slight tracking for metadata and property tags, echoing an editorial or architectural aesthetic.
- **Responsive Scaling**: Display and Large Headline sizes scale down for mobile devices to maintain visual balance and prevent overflow.

## Layout & Spacing

This design system utilizes a **Fixed Grid** model for desktop to maintain a curated, gallery-like feel.

- **Desktop**: 12-column grid with a 1280px max-width. Gutters are fixed at 24px to provide clear separation between property listings.
- **Tablet**: 8-column fluid grid with 24px side margins.
- **Mobile**: 4-column fluid grid with 16px side margins.

The spacing rhythm follows a **linear 8px scale**. Large vertical gaps (64px+) are encouraged between major sections to prevent the interface from feeling crowded, reinforcing the minimalist luxury narrative.

## Elevation & Depth

To maintain a high-end, contemporary feel, the system avoids heavy shadows in favor of **Tonal Layers** and **Low-Contrast Outlines**.

- **Surface Tiering**: The Cream (#F4F2E5) background acts as the base. Content containers, such as cards and modals, use Pure White (#FFFFFF) to create a subtle natural lift.
- **Shadows**: Shadows are used sparingly, reserved primarily for hover states on property cards and active dropdowns. These are extra-diffused and tinted with Dark Text Blue: `0 8px 30px rgba(27, 38, 49, 0.06)`.
- **Borders**: Structural definition is achieved through 1px Platinum (#C0C0C0) borders. This creates clear boundaries for inputs and headers without adding significant visual weight.

## Shapes

The shape language is **Soft (0.25rem)**. This subtle rounding softens the corporate edge, making the experience feel modern and approachable while remaining professional.

- **Standard Elements**: Buttons, input fields, and small UI components use the 4px (0.25rem) radius.
- **Container Elements**: Property cards and media containers utilize a larger **8px (0.5rem)** radius. This specific rounding for imagery and property containers mirrors modern architectural lines and creates a distinct framing effect for photography.

## Components

### Buttons
- **Primary**: Deep Blue background with white text. High contrast for key calls to action.
- **Secondary**: Platinum outline (1px) with Deep Blue text. 
- **Interactive State**: Hovering triggers a subtle darkening of the background and a light elevation shadow to provide tactile feedback.

### Input Fields
Minimalist execution featuring a 1px Platinum border on the Cream background. Upon focus, the border transitions to Deep Blue. Labels are strictly placed above the field using `label-md`.

### Property Cards
The core component of the system. Cards use a White surface with an 8px corner radius. They feature a full-bleed image at the top, followed by a price in Deep Blue and property metadata. Technical specs (beds, baths, area) are separated by Platinum vertical dividers.

### Navigation Bar
Fixed at the top of the viewport. Uses the Cream background with a subtle 1px Platinum bottom border for separation. Navigation links are set in Dark Text Blue, while the primary "List Your Property" CTA is styled as a primary button.

### Chips & Tags
Used for status indicators (e.g., "For Sale," "Featured"). These are non-interactive, pill-shaped elements with a 1px Platinum border and 12px text, intended to be used sparingly to avoid visual noise.