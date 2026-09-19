import { parseISO } from "date-fns";

/**
 * Parse a date-only API value ("YYYY-MM-DD", e.g. `month_start`, `demo_today`)
 * as a local calendar date. `new Date("YYYY-MM-DD")` parses as UTC midnight
 * per the ES spec, which formats as the *previous* local day in any
 * timezone west of UTC — always use this instead for calendar labels.
 */
export function parseDateOnly(value: string): Date {
  return parseISO(value);
}

/**
 * Parse a date-only API value into a UTC-anchored Date for arithmetic
 * (day counts, proration, month walking) rather than display. Pair with
 * the getUTC-prefixed getters and Date.UTC throughout the calculation —
 * never mix this with local getters (getMonth, getDate, new Date(y, m, d)),
 * which would read back a different calendar day in timezones west of UTC.
 */
export function parseDateOnlyUTC(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}
