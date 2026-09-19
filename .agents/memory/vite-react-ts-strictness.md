---
name: Vite react-ts scaffold TS strictness
description: Two build-breaking gotchas in the default `npm create vite@latest -- --template react-ts` tsconfig, relevant whenever hand-rolling shadcn-style UI primitives instead of running the shadcn CLI.
---

The default Vite react-ts scaffold (TypeScript ~6.0.2 era) ships a
`tsconfig.app.json` with `"baseUrl": "."`, which that TS version treats as
deprecated and turns into a hard build error under `tsc -b`.

**Why:** `tsc -b` failed with `TS5101: Option 'baseUrl' is deprecated` even
though the config otherwise matched the standard Vite template.

**How to apply:** add `"ignoreDeprecations": "6.0"` next to `baseUrl` in
`tsconfig.app.json` (needed for the `@/*` path alias pattern to keep working
without a rewrite).

Separately, this scaffold also enables `verbatimModuleSyntax`,
`noUnusedLocals`, and `noUnusedParameters`. When hand-rolling shadcn-style
components (skipping the interactive `shadcn` CLI), every file that
references `React.ReactNode`, `React.ComponentType`, `React.HTMLAttributes`,
etc. as a **type only** must import that type explicitly (e.g. `import type
{ ReactNode } from "react"`) — referencing the bare `React` namespace without
importing it (or importing it only as a value) fails to compile under
`verbatimModuleSyntax`. Files that also use `React.forwardRef` etc. as a
**value** should keep `import * as React from "react"` instead.
