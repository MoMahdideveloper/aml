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
The brand personality for the design system is **Sophisticated, Trustworthy, and Timeless**. It is designed specifically for high-end real estate, where the UI acts as a silent, premium gallery for property listings. 

The aesthetic follows a **Modern Minimalist** movement with **Corporate** undertones. It prioritizes clarity and whitespace to evoke a sense of breathing room and exclusivity. The interface avoids unnecessary decorative elements, instead using precise alignment and a refined color palette to communicate authority in the Iranian property market. The emotional response should be one of security—the user feels they are in the hands of an established, professional institution.

## Colors
The palette is derived from the heritage of the business card, optimized for digital accessibility and depth.

- **Deep Blue (#2A3A4B):** Used for primary brand elements, headers, and key interactive components. It represents stability.
- **Silver/Platinum (#C0C0C0):** Utilized as a sophisticated accent for borders, dividers, and secondary icons to add a metallic, high-end finish.
- **Cream/Off-white (#F4F2E5):** The primary background color. It provides warmth and reduces the clinical harshness of pure white, making long browsing sessions more comfortable.
- **Dark Text Blue (#1B2631):** Used for maximum legibility in body copy and titles, ensuring a high contrast ratio against the cream background.

## Typography
The system uses **IBM Plex Sans** (or **Vazirmatn** for Persian localized environments) to maintain a systematic and technical look. The hierarchy is strictly enforced to guide users through complex property data.

Headlines are set with tighter letter spacing and heavier weights to command attention, while body text uses generous line heights for maximum readability. For RTL (Persian) implementation, ensure font-weight consistency across the Vazirmatn family to match the "Heritage" aesthetic. Labels are occasionally uppercase with slight tracking to provide a professional, architectural feel to property tags and metadata.

## Layout & Spacing
This design system utilizes a **Fixed Grid** model for desktop to maintain the "premium gallery" feel, transitioning to a fluid model for mobile.

- **Desktop:** A 12-column grid with a 1280px max-width. Gutters are fixed at 24px to ensure distinct separation between property cards.
- **Tablet:** 8-column grid with 24px margins.
- **Mobile:** 4-column grid with 16px margins.

The spacing rhythm is based on a **linear 8px scale**. Larger gaps (64px+) are encouraged between sections to emphasize minimalism and prevent the interface from feeling "crowded," which is common in real estate portals.

## Elevation & Depth
To maintain a high-end feel, the system avoids heavy, muddy shadows. Instead, it uses **Tonal Layers** and **Low-Contrast Outlines**.

- **Surface Levels:** The primary background is the Cream (#F4F2E5). Cards and modals use a pure white (#FFFFFF) surface to "lift" them off the page.
- **Shadows:** Only used for interactive elements like hovered cards or open menus. Shadows are extra-diffused: `0 8px 30px rgba(27, 38, 49, 0.06)`. The tint is derived from the Dark Text Blue to keep it natural.
- **Borders:** Subtle 1px borders in Platinum (#C0C0C0) are used to define structural elements like input fields and headers without adding visual weight.

## Shapes
The shape language is **Soft (0.25rem)**. This slight rounding takes the edge off the "corporate" feel, making the brand more approachable while remaining firmly professional.

- **Buttons & Inputs:** Use the base 4px (0.25rem) radius.
- **Property Cards:** Use a larger 8px (0.5rem) radius to feel more like modern architectural containers.
- **Media/Imagery:** Property photos should always have an 8px radius to match the card containers.

## Components
### Buttons
Primary buttons use the Deep Blue (#2A3A4B) background with white text. Secondary buttons use a Platinum (#C0C0C0) outline with Deep Blue text. Hover states involve a slight darkening of the background and a subtle elevation lift.

### Input Fields
Inputs are minimalist: a 1px Platinum border on the Cream background. On focus, the border transitions to Deep Blue. Labels are always placed above the field in the `label-md` style.

### Property Cards
Cards are the heart of the system. They feature a full-width image at the top, followed by a padded section containing the price (in Deep Blue), property name, and a horizontal list of specs (beds, baths, sqm) separated by Platinum vertical dividers.

### Navigation Bar
The nav bar is fixed-top, using the Cream background with a subtle Platinum bottom border. It features the logo on the right (for RTL) or left, with navigation links in Dark Text Blue. A "List Your Property" CTA button is always highlighted in the primary Deep Blue.

### Chips/Tags
Used for "For Sale," "For Rent," or "Featured." These are small, non-interactive pills with a 1px border and 12px font size, used sparingly to prevent visual clutter.