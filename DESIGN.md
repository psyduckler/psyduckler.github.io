# Design System: psyduckler.com

## 1. Visual Theme & Atmosphere

psyduckler.com is a dark, terminal-native personal site that feels like SSH-ing into someone's brain — a near-black canvas (`#0d0d0d`) where monospace text glows in warm gold (`#f5c518`) against muted gray. The aesthetic is deliberately lo-fi: no images (except a single circular avatar), no gradients, no shadows, no border-radius on any element. This is a site that communicates personality through restraint — every pixel of decoration that's absent is a statement about what matters: the words.

The entire site is set in Berkeley Mono — a monospace font designed for code editors, with fallbacks to SF Mono, Fira Code, Consolas, and generic monospace. There are exactly two font weights: 400 (normal) for nearly everything, and 700 (bold) for emphasis. No medium, no semibold, no light — the binary weight system mirrors the terminal aesthetic where text is either regular or bold, nothing in between. The type scale spans just 7 sizes from 12px to 32px, with most content living in the 13.6px–15.2px range. Two elements use letter-spacing: section headings (`0.15em`) and blog dates (`0.1em`), both in uppercase — the only text-transform in the system.

What makes this site distinctive is its radical minimalism. The color system uses exactly 5 CSS custom properties: `--bg`, `--fg`, `--accent`, `--muted`, `--link`. The only decorative element is a blinking terminal cursor (CSS animation) after the tagline. Links reveal themselves through a border-bottom that transitions from transparent to gold on hover. Sections are separated by `1px solid #1a1a1a` borders — barely visible lines that create structure from darkness. The 600px max-width container with generous padding creates a reading column that feels like a personal letter, not a webpage.

**Key Characteristics:**
- Near-black canvas (`#0d0d0d`) — darker than most dark themes, approaching true terminal black
- Gold accent (`#f5c518`) as singular brand color — warm, IMDb-yellow, used for h1, links, project titles, avatar border, and list bullets
- Berkeley Mono throughout — monospace-only, no sans-serif, no serif
- 5 CSS custom properties only: `--bg`, `--fg`, `--accent`, `--muted`, `--link`
- Zero shadows, zero gradients, zero border-radius (except 50% avatar)
- Binary weight system: 400 or 700, nothing in between
- 600px max-width container — narrow reading column
- `1px solid #1a1a1a` as the universal divider — sections, cards, footer
- Blinking terminal cursor animation on tagline
- Single breakpoint at 480px — brutally simple responsive design

## 2. Color Palette & Roles

### CSS Custom Properties (defined on `:root`)
```css
--bg: #0d0d0d;
--fg: #e0e0e0;
--accent: #f5c518;
--muted: #666;
--link: #f5c518;
```

### Primary
- **Terminal Black** (`#0d0d0d`): `--bg`. Page background — near-pure black with no blue/warm undertone. Raw darkness.
- **Light Gray** (`#e0e0e0`): `--fg`. Primary body text. Soft enough to avoid eye strain on dark, warm enough to feel human.
- **Gold** (`#f5c518`): `--accent` / `--link`. The singular accent color. Used for: site name (h1), project titles, blog post titles, links, avatar border, now-list bullet arrows, nav active/hover state.

### Secondary
- **Muted Gray** (`#666666`): `--muted`. Secondary text: tagline, nav links (default state), dates, section labels, project link text, footer text.
- **Divider Dark** (`#1a1a1a`): Border/divider color — barely visible against the background, creating whisper-thin structural lines.

### That's It
Five colors. One divider tone. No gradients, no alpha variations, no semantic status colors. The constraint is the system.

## 3. Typography Rules

### Font Family
- **Primary (and only)**: `'Berkeley Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace`
- **No secondary font** — monospace everywhere, headers to footer.
- **No OpenType features** beyond what Berkeley Mono provides by default.

### Hierarchy

| Role | Size | Weight | Line Height | Letter Spacing | Text Transform | Color | Notes |
|------|------|--------|-------------|----------------|----------------|-------|-------|
| Site Name | 32px (2rem) | 400 | normal | normal | none | `--accent` (#f5c518) | h1 — notably uses weight 400, not bold |
| Blog Post Title | 17.6px (1.1rem) | 400 | 1.7 | normal | none | `--accent` (#f5c518) | h3 — links styled as accent |
| Section Label | 12px (0.75rem) | 400 | 1.7 | 0.15em | uppercase | `--muted` (#666) | h2 with bottom border |
| Section Paragraph | 15.2px (0.95rem) | 400 | 1.7 | normal | none | `--fg` (#e0e0e0) | Standard reading text |
| Now List Item | 15.2px (0.95rem) | 400 | 1.7 | normal | none | `--fg` (#e0e0e0) | With → bullet in accent |
| Project Title | 16px (1rem) | 400 | 1.7 | normal | none | `--accent` (#f5c518) | Project name in header row |
| Project Description | 14.4px (0.9rem) | 400 | 1.7 | normal | none | `--fg` (#e0e0e0) | Below project header |
| Project Links | 12.8px (0.8rem) | 400 | 1.7 | normal | none | `--muted` (#666) | "site · github" links |
| Tagline | 13.6px (0.85rem) | 400 | 1.7 | normal | none | `--muted` (#666) | Below site name + blink cursor |
| Nav Link | 13.6px (0.85rem) | 400 | 1.7 | normal | none | `--muted` (#666) | Default state; accent on hover/active |
| Blog Date | 12px (0.75rem) | 400 | 1.7 | 0.1em | uppercase | `--muted` (#666) | Above blog post title |
| Footer | 12px (0.75rem) | 400 | 1.7 | normal | none | `--muted` (#666) | Copyright line |
| Body Bold | inherit | 700 | 1.7 | normal | none | inherit | Inline `<strong>` emphasis only |

### Principles
- **Weight 400 is king**: Even the h1 site name uses weight 400. The only 700 usage is inline `<strong>` tags within body text. This creates a uniform, terminal-like texture where hierarchy comes from size and color, not weight.
- **Monospace is the identity**: Berkeley Mono isn't a styling choice — it IS the brand. Every character occupies the same width, creating a grid-like reading rhythm that says "this person codes."
- **Two letter-spacing modes**: `0.15em` for section labels, `0.1em` for dates — both uppercase. Everything else is `normal`. The expanded tracking + uppercase combination creates a structural "label" pattern.
- **Line-height 1.7 everywhere**: A single, generous line-height across the entire site. No tight headlines, no compressed navigation. Uniform vertical rhythm.

## 4. Component Stylings

### Avatar
- Width/Height: 120px
- Border-radius: 50% (the ONLY border-radius in the system)
- Border: `2px solid #f5c518` (accent)
- Object-fit: cover
- Margin-bottom: 1rem
- Notes: The only image on the site. The only rounded element. The only decorative border.

### Section Heading (h2)
- Font: 12px Berkeley Mono, weight 400
- Text-transform: uppercase
- Letter-spacing: 0.15em
- Color: `#666666` (muted)
- Padding-bottom: 0.5rem
- Border-bottom: `1px solid #1a1a1a`
- Margin-bottom: 1rem
- Use: "now", "projects", "latest post", "blog", "about", "elsewhere"

### Project Card
- Structure: flex header (title + links) → description paragraph
- Title: 16px, accent gold
- Links: 12.8px, muted gray, separated by `·`
- Description: 14.4px, foreground gray
- Divider: `1px solid #1a1a1a` (bottom border + padding-bottom)
- Spacing: 1.5rem margin-bottom, 1.5rem padding-bottom
- Last child: no border, no bottom margin

### Blog Entry
- Structure: date → title (link) → body text
- Date: 12px uppercase, 0.1em tracking, muted
- Title: 17.6px, accent gold (linked)
- Body: 15.2px, foreground gray
- Divider: `1px solid #1a1a1a` (bottom border)
- Spacing: 2.5rem margin-bottom, 2rem padding-bottom

### Now List
- List-style: none (custom bullets)
- Bullet: `→` via `::before` pseudo-element in accent gold
- Item padding: 0.4rem vertical
- Font: 15.2px, foreground gray
- Links within: accent gold with hover underline

### Links
- Color: `#f5c518` (accent gold)
- Text-decoration: none
- Border-bottom: `1px solid transparent`
- Transition: `border-color 0.2s`
- Hover: `border-bottom-color: #f5c518`
- Notes: The hover underline reveal is the only interactive animation besides the blink cursor

### Navigation
- Font: 13.6px, muted gray
- Link spacing: `margin-right: 1.5rem`
- Default: muted gray text
- Active/Hover: accent gold text
- Hover: adds bottom border in accent
- Margin-bottom: 2rem below nav
- Links: "home", "about", "blog"

### Footer
- Margin-top: 4rem
- Padding-top: 1.5rem
- Border-top: `1px solid #1a1a1a`
- Font: 12px, muted gray
- Content: copyright text

### Blink Cursor
- Selector: `.blink`
- Animation: `blink 1.2s step-end infinite`
- Keyframe: `50% { opacity: 0 }`
- Use: Terminal-style blinking cursor character after tagline text

## 5. Layout Principles

### Spacing System
- Base: rem units on 16px root
- 4px (0.25rem): h1 margin-bottom
- 6.4px (0.4rem): now-list item vertical padding
- 8px (0.5rem): section h2 padding-bottom, project header gap
- 12px (0.75rem): blog title margin-bottom
- 16px (1rem): section paragraph margin-bottom, avatar margin-bottom
- 20px (1.25rem): mobile body horizontal padding
- 24px (1.5rem): header margin-bottom, project/footer padding, nav link spacing
- 32px (2rem): h1 size, desktop horizontal padding, blog entry padding-bottom
- 40px (2.5rem): section margin-bottom, blog entry margin-bottom
- 64px (4rem): desktop body top/bottom padding, footer margin-top

### Grid & Container
- **Body**: `display: flex; justify-content: center; min-height: 100vh`
- **Container**: `max-width: 600px; width: 100%`
- **Padding**: `4rem 2rem` (desktop), `2rem 1.25rem` (mobile)
- No grid system. No columns. Single-column throughout.

### Whitespace Philosophy
- **Narrow reading column**: 600px max-width creates an intimate, letter-like reading experience. On a 1440px screen, over half the viewport is empty darkness — the content floats in a void.
- **Generous vertical breathing**: 2.5rem between sections, 4rem above footer. The spacing is leisurely, not dense.
- **Darkness as negative space**: The near-black background IS the whitespace. Empty space doesn't feel empty — it feels like a terminal waiting for input.
- **Single-column purity**: No sidebars, no multi-column layouts, no grids. One column of text, top to bottom.

### Border Radius Scale
- 0px: Everything
- 50%: Avatar only

That's the entire scale. The absence of border-radius is the design decision.

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow, `#0d0d0d` bg | Everything |

**Shadow Philosophy**: There are no shadows. Zero. The site is perfectly flat — a terminal has no depth, and neither does this. Elevation is communicated solely through color: accent gold elements "pop" not because they're raised, but because they're bright against darkness. The `1px solid #1a1a1a` dividers create structure through near-invisible lines, not through shadow or elevation.

## 7. Do's and Don'ts

### Do
- Use `#0d0d0d` (near-black) as the background — darker than most dark themes
- Apply gold (`#f5c518`) only for accent elements: titles, links, avatar border, list bullets
- Use Berkeley Mono (or monospace fallback) for ALL text — no exceptions
- Keep font-weight at 400 for everything except inline bold (700)
- Use `1px solid #1a1a1a` for all structural dividers
- Maintain 600px max-width for content — the narrow column is intentional
- Use `#e0e0e0` for primary text and `#666666` for secondary — the two-tone system
- Keep uppercase + letter-spacing for section labels and dates only
- Use the 5 CSS custom properties for all colors

### Don't
- Don't add shadows — the flat aesthetic is absolute
- Don't add border-radius to anything except the avatar (50%)
- Don't add gradients or background patterns — pure solid `#0d0d0d`
- Don't use sans-serif or serif fonts — monospace only, always
- Don't use font weights between 400 and 700 — binary weight system
- Don't add images (except avatar) — the site is text-only by design
- Don't use more than the 5 established colors — constraint is the system
- Don't use animations beyond the blink cursor and link border transition
- Don't make the container wider than 600px — the intimacy is intentional
- Don't use warm colors (orange, red) or cool colors (blue, green) — gold and gray only

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | ≤480px | Reduced padding, smaller h1 |
| Desktop | >480px | Full layout |

That's it. One breakpoint. The 600px max-width means the site is inherently mobile-friendly — the only responsive change is reducing padding and the h1 size.

### Mobile Changes
- Body padding: `4rem 2rem` → `2rem 1.25rem`
- h1 font-size: `2rem` (32px) → `1.5rem` (24px)
- Everything else stays the same

### Touch Targets
- Nav links: 13.6px with 1.5rem spacing — adequate for touch
- Blog titles: full-width block links
- Project links: 12.8px — small but functional
- Now list links: inline within 15.2px text

### Collapsing Strategy
There is no collapsing. The single-column layout at 600px max-width works at every viewport. No hamburger menu, no stacking, no grid changes. The design is mobile-first by being narrow-first.

## 9. Agent Prompt Guide

### Quick Color Reference
- Background: Terminal Black (`#0d0d0d`)
- Primary text: Light Gray (`#e0e0e0`)
- Accent/Link: Gold (`#f5c518`)
- Secondary text: Muted Gray (`#666666`)
- Divider: Dark Line (`#1a1a1a`)

### Example Component Prompts
- "Create a personal site header: `#0d0d0d` background. 120px circular avatar with `2px solid #f5c518` border. Site name at 32px Berkeley Mono weight 400, `#f5c518`. Tagline at 13.6px weight 400, `#666666`, with blinking cursor animation."
- "Design a section: 12px Berkeley Mono uppercase heading, `0.15em` letter-spacing, `#666666` text, `1px solid #1a1a1a` bottom border, `0.5rem` padding-bottom. Content at 15.2px weight 400, `#e0e0e0`, line-height 1.7."
- "Build a project card: flex header with title (`#f5c518`, 16px) and links (`#666666`, 12.8px, separated by ·). Description at 14.4px `#e0e0e0`. Bottom border `1px solid #1a1a1a`."
- "Create a blog entry: date at 12px uppercase `#666666` with `0.1em` letter-spacing. Title at 17.6px `#f5c518` weight 400 (linked). Body at 15.2px `#e0e0e0`. Bottom border `1px solid #1a1a1a`."
- "Design navigation: 13.6px Berkeley Mono, `#666666` default, `#f5c518` on hover/active. Links spaced 1.5rem apart. Hover adds `1px solid #f5c518` bottom border with 0.2s transition."

### Iteration Guide
1. Start with `#0d0d0d` — the darkness is the canvas, not a theme applied to a light design
2. Five colors only: `#0d0d0d`, `#e0e0e0`, `#f5c518`, `#666666`, `#1a1a1a`
3. Berkeley Mono everywhere — the monospace font IS the brand identity
4. Weight 400 for everything, 700 only for inline `<strong>` emphasis
5. No shadows, no gradients, no border-radius (except 50% avatar)
6. `1px solid #1a1a1a` for all structural dividers — barely visible, always present
7. 600px max-width container — the narrow column creates intimacy
8. Line-height 1.7 globally — generous, uniform vertical rhythm
9. Gold (`#f5c518`) is the only accent — it marks what matters: your name, your work, your links
10. The constraint IS the design — don't add, subtract
