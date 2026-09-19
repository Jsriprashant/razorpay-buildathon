---
name: Date-only arithmetic and display must avoid JS Date/UTC-local mixing
description: A YYYY-MM-DD value parsed with `new Date(string)` is UTC midnight, but local getters/formatters (getMonth/getDate, date-fns `format`, `new Date(y,m,d)`) read local time — mixing the two silently shifts results in timezones west of UTC.
---

# Date-only arithmetic and display must avoid JS Date/UTC-local mixing

`new Date("2026-03-01")` (a bare `YYYY-MM-DD` string) is parsed as UTC
midnight per the ES spec. Any local-time read of that value —
`.getMonth()`/`.getDate()`, `new Date(y, m, d)` built from its local
getters, or a formatter like date-fns `format()` that renders in local
time — can silently shift the result back a calendar day in any timezone
west of UTC. This breaks both date *arithmetic* (proration, day counts,
"is this in the past" checks) and plain *display* (a month/date label
showing the wrong month).

**Why:** caught twice by code review in this project — once in a form that
previewed a backend-computed value from start/end dates (proration), and
again in cycle/rollover/demo-clock UI that labels a month or date purely
for display. Both are the same root cause: a date-only string flowing into
local-time-sensitive code.

**How to apply:** for any date-only (no time-of-day) field coming from an
API in JS/TS:
- Parsing for **display**: use a parser that treats the string as a local
  calendar date, not UTC — e.g. date-fns `parseISO(dateOnlyString)` — then
  format normally. Never call `new Date(dateOnlyString)` directly for a
  label.
- **Arithmetic**: either parse year/month/day manually and stay in UTC
  throughout (`Date.UTC(y, m, d)` / `getUTCMonth()` etc.), or use a
  date-only library that never touches local time. Never let a value born
  from `new Date(dateOnlyString)` flow into local-time getters or
  constructors.
- When the calculation also matters on the backend (money, proration,
  contract windows), add a parity check comparing the frontend preview
  against the backend's actual computed value for at least one non-UTC-like
  timezone case.
