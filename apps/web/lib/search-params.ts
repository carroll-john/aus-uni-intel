// Helpers for reading Next.js search params (which may be string | string[]).

export function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function many(value: string | string[] | undefined, fallback: string[]): string[] {
  if (Array.isArray(value)) return value.flatMap((item) => item.split(",")).filter(Boolean);
  if (value) return value.split(",").filter(Boolean);
  return fallback;
}

export function pickOption(value: string | undefined, allowed: string[]): string | undefined {
  return value && allowed.includes(value) ? value : undefined;
}

export function distinct(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}
