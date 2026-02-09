# UI/UX Redesign Vision

## Current State (completed)
- SEO-friendly URLs with full book slugs (`/bible/genesis/1/1/bereshit/`)
- Individual verse pages (~23K) and word pages (~306K)
- Hebrew transliteration, morphology, lexicon data on word pages
- Functional but muted/technical-looking — feels API-focused, not inviting

## Vision
Transform the site from a technical tool into a warm, modern, educational resource that serves the Scattered Israelites ministry mission. Detailed and informational, but user-friendly and accessible to people who aren't Hebrew scholars.

### Core Principles
- **Inviting, not industrial** — modern, responsive, beautiful design people want to spend time on
- **Detailed but accessible** — academic rigor with plain-language explanations
- **Ministry-aligned** — tied to the Scattered Israelites book series whose goal is to lead the Israelites, and anyone who will hear, back to Yahweh through Yehoshua for repentance and forgiveness of sins
- **Transparent** — honest about manuscript sources and how the site was built

## Pages to Design

### 1. Home Page (`/`)
- Landing page introducing the mission
- Features the Bible reader prominently
- Connects to the book series + YouTube
- Clear call to action

### 2. Book List (`/bible/`)
- Warm, browseable grid of all 39 OT books
- Possibly grouped by section (Torah, Prophets, Writings)

### 3. Book Page (`/bible/genesis/`)
- **Book introduction** — what the book is about, themes
- **Historical context** — when likely written and compiled, authorship
- **Redemptive thread** — how the book points to redemption in Yehoshua
- Chapter picker below the introduction

### 4. Chapter View (`/bible/genesis/1/`)
- Interlinear Hebrew with glosses (existing)
- More inviting visual treatment
- Make morphology codes less intimidating

### 5. Verse Page (`/bible/genesis/1/1/`)
- Verse in context with word links
- Word table with accessible labels
- User-friendly explanations alongside technical data

### 6. Word Page (`/bible/genesis/1/1/bereshit/`)
- Large Hebrew display with transliteration and meaning
- Verse context with current word highlighted
- Morphology explained in plain language (not just "Qal perfect 3ms")
- Lexicon entry
- Word construction / morphemes

### 7. About Page
- The manuscript: OSHB (Open Scriptures Hebrew Bible), what it is, why it was chosen
- How the site was built — transparency about methodology
- The mission of Scattered Israelites

### 8. Static/Ministry Pages
- Link to YouTube channel
- Link to purchase the Scattered Israelites book series
- Contact or community info

## Open Questions (to decide before building)

### Content
- **Book introductions (39 books)**: Write yourself (theological perspective about Yehoshua and repentance is personal) or draft for review?
- **Plain-language morphology labels**: e.g. "Qal perfect 3ms" → "Simple past tense, he did (third person, masculine, singular)"

### Design
- **Color palette / brand identity**: Does the Scattered Israelites series have brand colors, a logo, or a visual direction? (earthy/ancient? clean/modern? warm tones?)
- **Typography**: Keep current Hebrew font stack? Add a specific English display font?
- **Layout style**: Cards? Sidebar navigation? Full-width sections?

### Technical
- **Book model changes**: Need to add fields for introduction text, author, date range, themes, etc. (or a separate `BookIntroduction` model)
- **Static pages**: Django flatpages, or just templates?
- **Home page**: New app or just a view in the existing reader app?

## Suggested Phases

### Phase 1: Visual Foundation
- New color palette, typography, layout system
- Redesign base.html with new nav, footer, branding
- Update book list page styling

### Phase 2: Book Pages
- Add book introduction model/content
- Design and build the book detail page with intro, context, redemptive thread
- Write or draft book introductions (start with Torah)

### Phase 3: Reading Experience
- Redesign chapter view — warmer, more readable
- Make verse and word pages more accessible
- Add plain-language morphology helpers

### Phase 4: Ministry Integration
- Build home page (`/`)
- About page with manuscript transparency
- YouTube channel link, book series purchase links
- Footer with ministry info

### Phase 5: Polish
- Mobile responsive refinement
- Loading states, transitions
- SEO refinement (structured data, sitemap)
