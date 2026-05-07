---
name: redesign-saas
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface — left vertical sidebar (replacing top nav), header bar with breadcrumbs and user menu, dark/light theme scaffolding, consistent design tokens for spacing, type, color, radius, and shadow. Use when the user asks to "redesign the UI", "modernize the look", "make it look like a SaaS app", "switch to a left sidebar", or similar visual overhauls. Tested on Vue 3 + Composition API + Vite apps.
---

# Redesign Vue 3 App as a Modern SaaS Dashboard

This skill turns a typical Vue 3 app with a top nav into a polished SaaS-style dashboard with a left vertical sidebar, a content header, consistent spacing, and a light/dark theme. Apply it when the user wants a visual overhaul, not when they want a single component restyle.

## Reference files in this skill

Located in `references/` next to this `SKILL.md`. Read them before you start; they contain the shapes and tokens you should mirror in the target codebase.

- `tokens.css` — full set of CSS custom properties for spacing, color, radius, shadow, type. Includes a light theme on `:root` and a dark theme on `[data-theme="dark"]`. Drop-in.
- `sidebar-shell.vue` — reference layout for the new `App.vue`: sidebar + content header + scroll region. Annotated. Adapt the route names / labels / icons to the target app.
- `theme-composable.js` — `useTheme()` composable: toggles `data-theme` on `<html>`, persists to localStorage, respects `prefers-color-scheme` on first load.
- `target-mockup.html` — static HTML mockup of the target look. Open it in a browser before you start so you have a visual reference. Treat it as a north star, not a pixel-perfect spec.

## Mandatory rules from this project

- **Always delegate `.vue` file creation or significant edits to the `vue-expert` subagent**, per the root `CLAUDE.md`. The shell rewrite, sidebar component, and per-view audits all qualify.
- **Document non-obvious logic with a comment** (project rule). For visual changes this rarely applies; for the theme composable and any keyboard shortcut handling, add a short `// why:` line.
- **No emojis in UI** (project rule, from `CLAUDE.md`). Use icon glyphs from `lucide-static`, inline SVG, or unicode geometric characters — never emojis.

## Workflow

Run these phases in order. Don't skip the audit.

### Phase 1 — Audit

Goal: know what you're changing before you change it.

1. Identify the shell file (usually `client/src/App.vue` or `src/App.vue`) and the route registry (`main.js` or `router/index.js`).
2. List every view in `views/` and grep for top-level layout markup that the redesign will touch (`page-header`, `nav-tabs`, container divs that fight the new shell).
3. Note any existing design tokens. If `:root` already defines CSS variables, decide whether to extend or replace. Replace only if they're sparse or inconsistent; extend otherwise.
4. List every place that uses an emoji or a one-off color literal. These get replaced in Phase 5.
5. Identify i18n setup if present. New nav labels need keys in every locale file.

Report the audit before editing. Two paragraphs or a short bulleted list is enough.

### Phase 2 — Tokens

Drop `references/tokens.css` into a global stylesheet. Two patterns work:

- **Inject into `App.vue`** under a non-scoped `<style>` block so the variables are global.
- **Add a separate `src/assets/tokens.css`** and import it once in `main.js` (`import './assets/tokens.css'`).

Prefer the separate file approach when the project already has a `main.js` import for global CSS. Strip any color/spacing literals from existing global styles that conflict.

After this phase, verify with the dev server that nothing visually broke.

### Phase 3 — Shell

Replace the top nav with the sidebar shell. Delegate to `vue-expert` with this brief:

> Rewrite `App.vue` to match the structure in `references/sidebar-shell.vue`. Keep the existing `<router-view />`, language switcher, profile menu, and modal mounts. Move filter bars (if any) into the content header so they remain visible. Preserve all router-link `to` paths — only the markup around them changes. Use the design tokens defined in `tokens.css` (var(--space-4), var(--color-text-muted), etc.). Do not introduce new global CSS classes; rely on tokens.

Sidebar requirements:
- Fixed width 240px expanded, 64px collapsed. Persist collapsed state via `useTheme`-style composable or a small `useLayout` ref backed by localStorage.
- Each nav item has an icon (16-20px) + label. Active state: tinted background + accent border-left. Hover state: subtle background.
- Logo at the top. User menu / theme toggle at the bottom (sticky).
- On viewport `< 900px`, collapse to icon-only automatically.
- Keyboard: `[` and `]` toggle collapse (add a `// why:` comment on the keydown listener).

### Phase 4 — Header

Add a content header that lives at the top of the right-hand scroll region (not the page itself). It contains:
- Breadcrumbs derived from the current route (use `useRoute().path`).
- An optional page-action slot for buttons like "New", "Export", filter dropdowns.
- A user menu / theme toggle on the right (the latter mirrors what's in the sidebar so users on small screens can find it).

The breadcrumbs should be data-driven from a small `route → label` map (or `route.meta.breadcrumb`). Don't hardcode per-route components.

### Phase 5 — View polish

Walk every file in `views/` and apply consistent patterns:

- Replace `<div class="page-header">` blocks with the header slot pattern from Phase 4. The big H2 + paragraph that lived inside each view either moves to the header or gets removed if the breadcrumb already says it.
- Cards: `border-radius: var(--radius-lg)`, `border: 1px solid var(--color-border)`, `background: var(--color-surface)`, `padding: var(--space-6)`. Drop heavy box-shadows; rely on a single `--shadow-sm` for elevation.
- Tables: replace zebra striping with a single subtle border, sticky header, compact row height (40-44px), monospace numerics for currency / counts.
- Buttons: standardize to `.btn` + variants (`.btn-primary`, `.btn-ghost`, `.btn-danger`). Replace inline color literals.
- Status badges: tokenize. The existing `.badge.success/.info/.warning/.danger` classes can stay if they already use tokens; otherwise refactor.
- Spacing: replace ad-hoc `margin: 1.5rem 0` with `var(--space-6)`. Replace ad-hoc `gap: 1rem` with `var(--space-4)`.
- Remove any emoji characters; replace with inline SVG icons or unicode geometric shapes.

Each view rewrite is a `vue-expert` delegation. Bundle 2-3 related views per call to avoid a chatty back-and-forth.

### Phase 6 — Verify

1. Run the dev server (use the project's existing `start` skill if it exists; otherwise `npm run dev` in the client directory).
2. Walk every route. Confirm the sidebar highlights the active route, the header shows the right breadcrumb, and no view escapes the content container's max width.
3. Toggle dark mode via the theme button. Verify cards, tables, badges, and charts stay readable.
4. Resize the viewport to ~800px wide. Confirm the sidebar collapses automatically.
5. Run any test suite the project has. Visual changes shouldn't break tests; if they do, the test was probably scraping DOM structure that the redesign changed — fix the test, not the markup.
6. Take one full-page screenshot per route into `docs/redesign/<route>.png` if the user wants a record.

## Common pitfalls

- **Don't redefine global classes inside scoped styles.** Cards and tables look broken because the scoped `.card` rule shadows the global one. If you need to override, use a more specific class.
- **Don't mix the new tokens with the old palette.** Pick one source of truth. If a view still imports literal hex codes, it'll drift from the rest.
- **Don't duplicate the page header inside views and inside the content header.** Pick one home for the page title; the breadcrumb usually wins.
- **Don't ship dark mode broken.** If the user picks the full-template scope, every view must work in both themes. If you can't get one working in time, ship light-only and remove the toggle, don't ship a half-working dark mode.
- **Don't move filter bars without thinking.** If a `FilterBar` was a child of `App.vue`, putting it in the new content header is fine. If filters are per-page, keep them in the page.

## Out of scope

- Component library swap (e.g., adopting Naive UI, Vuetify). This skill assumes you're keeping the project's hand-rolled components and just restyling them.
- Build tooling changes (Vite plugins, PostCSS, Tailwind). The tokens.css approach is intentionally framework-free.
- Routing changes. Routes stay the same; only the chrome around `<router-view />` changes.
