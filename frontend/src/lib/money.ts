/**
 * The one shared frontend money formatter (Section 2: "one frontend format
 * helper; currency comes from settings"). Never do money math in the UI —
 * every number is computed server-side in whole cents.
 */
const SYMBOLS: Record<string, string> = { USD: "$", EUR: "\u20ac", GBP: "\u00a3", INR: "\u20b9" };

export function formatCents(cents: number, currency: string = "USD"): string {
  const symbol = SYMBOLS[currency] ?? `${currency} `;
  const sign = cents < 0 ? "-" : "";
  const magnitude = Math.abs(cents);
  const dollars = Math.floor(magnitude / 100);
  const remainder = magnitude % 100;
  return `${sign}${symbol}${dollars.toLocaleString()}.${remainder.toString().padStart(2, "0")}`;
}
