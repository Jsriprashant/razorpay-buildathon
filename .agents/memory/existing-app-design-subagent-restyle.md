---
name: Restyling an existing (non-scaffold) fullstack app with design subagents
description: How to use the design-subagent workflow when the app is hand-rolled rather than the artifacts/<slug> generated-client scaffold the design skill assumes.
---

The design skill's fullstack-app guidance (`.local/skills/design/SKILL.md`) is written for greenfield `artifacts/<slug>` scaffolds with a generated API client. It still works for a full visual overhaul of an existing hand-rolled app (custom `lib/api.ts`, hand-written types, no codegen), with two adaptations:

1. Do the foundational design-system work yourself first, directly: theme tokens (CSS variables), Tailwind config, and every shared UI primitive (button/card/badge/tabs/input/dialog) plus the app shell (sidebar/topbar/page header). Prove it out on one full page (e.g. the home dashboard and the login page) before delegating anything.
2. Delegate the remaining pages to `$kind: "design"` subagents grouped by role/area (e.g. one subagent per role's page set), with `outputDir` set to the real app directory (not a fresh scaffold path). Pass the already-updated shared component files and one or two fully-restyled reference pages via `relevantFiles` so subagents extend the established system instead of inventing a competing one. Explicitly tell them not to touch theme tokens or shared primitives unless there's a genuine gap, and not to change API calls/routes/business logic — this is a pure visual restyle of pages already wired to real data.

**Why:** without an established system to point to, parallel design subagents restyling different page groups will each invent their own colors/radii/spacing, producing an inconsistent app. Grounding them in real, already-edited files (not a prose spec) is what keeps multi-subagent restyles visually coherent.

**How to apply:** any future "redesign the whole app" request on a hand-rolled (non-generated-client) fullstack app in this workspace pattern.
