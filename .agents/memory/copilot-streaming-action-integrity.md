---
name: Copilot streaming and action integrity
description: Product and security rules for live Copilot responses and confirmed write actions.
---

Copilot streams answer text plus concise status and verified tool activity. It must never expose private chain-of-thought or fabricate progress. Partial, stopped, or incomplete provider responses are not valid conversation history.

**Why:** users need visible progress without leaking hidden reasoning, and interrupted streams must not contaminate later answers.

**How to apply:** stream explicit status/tool/answer/done events; require a provider completion event; guard browser stream cleanup by request identity.

Copilot token budgets are phase-aware: tool-selection rounds get a bounded initial budget, final synthesis gets more room, and `max_output_tokens` incompletes continue with minimal reasoning instead of failing immediately. History and large tool payloads must be bounded before each provider call.

**Why:** reasoning tokens, tool-call JSON, and answer text share the output allowance. A single low fixed limit can truncate a valid multi-step action after some work has already completed.

**How to apply:** preserve already streamed text, continue without repetition up to a hard ceiling, keep only the newest history within a character budget, cap large result collections with explicit truncation metadata, and never automatically replay confirmed write mutations.

Copilot write confirmations use persisted, one-time, user-and-team-bound action grants. The signed capability is delivered only to the browser, never included in tool output sent back to the model. A replay returns the stored result rather than running the mutation again.

**Why:** signing a client-carried payload prevents tampering but does not prevent replay; a valid token could otherwise create duplicate records.

**How to apply:** atomically claim the server-side grant before mutation, store the action result for idempotent replay, and reject invalid, expired, cross-user, or cross-team capabilities.