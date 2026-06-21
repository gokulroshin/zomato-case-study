---
name: Vibrant Noir
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#e4bebc'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#ab8987'
  outline-variant: '#5b403f'
  surface-tint: '#ffb3b1'
  primary: '#ffb3b1'
  on-primary: '#680011'
  primary-container: '#ff535a'
  on-primary-container: '#5b000e'
  inverse-primary: '#bb162c'
  secondary: '#c8c6c6'
  on-secondary: '#303030'
  secondary-container: '#474747'
  on-secondary-container: '#b6b5b4'
  tertiary: '#71d7cf'
  on-tertiary: '#003734'
  tertiary-container: '#32a099'
  on-tertiary-container: '#00302d'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#e4e2e1'
  secondary-fixed-dim: '#c8c6c6'
  on-secondary-fixed: '#1b1c1c'
  on-secondary-fixed-variant: '#474747'
  tertiary-fixed: '#8ef4eb'
  tertiary-fixed-dim: '#71d7cf'
  on-tertiary-fixed: '#00201e'
  on-tertiary-fixed-variant: '#00504c'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 16px
  margin-mobile: 20px
  margin-desktop: auto
---

## Brand & Style
The design system balances high-energy hospitality with a premium, late-night aesthetic. It targets an audience that values speed, curation, and culinary exploration. The visual style is **Corporate Modern** with **Minimalist** influences, relying on deep ink tones to make food photography and primary actions pop.

The emotional response should be one of hunger-inducing excitement tempered by a sophisticated, effortless user experience. Heavy whitespace (or "darkspace") and precise typography ensure that despite the vibrant accent color, the interface remains grounded and professional.

## Colors
The palette is anchored by a deep obsidian background to provide a "premium dark mode" feel. 

- **Primary:** The vibrant Zomato Red (#E23744) is the focal point. It is used exclusively for primary intent: call-to-action buttons, active states of sliders, progress bars, and critical highlights.
- **Secondary:** A warm charcoal used for card surfaces and container backgrounds to create subtle separation from the pure black canvas.
- **Neutral:** A systematic range of grays for borders and secondary text, ensuring the red remains the most dominant chromatic element on the screen.

## Typography
This design system utilizes **Be Vietnam Pro** for headlines to convey a contemporary and inviting character. Its geometric yet friendly terminals pair perfectly with the vibrant red accent. For body copy and functional labels, **Plus Jakarta Sans** provides exceptional legibility and a soft, professional tone.

- **Scale:** High contrast between display titles and body text to establish a clear information hierarchy.
- **Weights:** Bold weights are reserved for brand moments and primary navigation, while Medium and Regular weights handle high-density information.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a maximum content width of 1280px for desktop. 

- **Desktop:** 12-column grid with 24px gutters.
- **Mobile:** 4-column grid with 16px gutters and 20px side margins.
- **Rhythm:** An 8px linear scale governs all padding and margins to maintain vertical rhythm. Larger gaps (40px+) are encouraged between distinct content sections to reinforce the minimalist brand pillar.

## Elevation & Depth
Depth is achieved through **Tonal Layers** rather than heavy shadows. In this dark mode environment, higher elevation is represented by lighter surface colors.

- **Level 0 (Background):** #121212 (Base canvas).
- **Level 1 (Cards/Sheet):** #1E1E1E (Subtle lift).
- **Level 2 (Popovers/Modals):** #2D2D2D (Maximum lift).
- **Accents:** The primary red should never have a shadow; instead, it uses a subtle 10-15% opacity red outer glow (glow-blur) when used on interactive elements like floating action buttons to simulate "light" in a dark environment.

## Shapes
The shape language is **Rounded**, reflecting the approachable and friendly nature of the food and social categories. 

- **Standard Elements:** Buttons and input fields use a 0.5rem (8px) corner radius.
- **Large Containers:** Cards and modals utilize 1rem (16px) to soften the overall interface.
- **Icons:** Use a consistent 2px stroke width with rounded caps and joins to match the component geometry.

## Components
- **Buttons:** Primary buttons are solid #E23744 with white text. Secondary buttons use a transparent background with a 1px border of #2D2D2D.
- **Sliders:** The track uses #2D2D2D, while the filled portion and the thumb use #E23744.
- **Chips:** Categorical chips use a #1E1E1E fill. Selected chips transition to a #E23744 fill with white text.
- **Input Fields:** Use a #1E1E1E background with a subtle bottom border. Upon focus, the border transitions to #E23744.
- **Cards:** Image-heavy with a slight gradient overlay at the bottom to ensure white typography remains legible over food photography.
- **Lists:** Clean dividers using #1E1E1E; interactive list items show a subtle #FFFFFF (0.05 opacity) highlight on hover.