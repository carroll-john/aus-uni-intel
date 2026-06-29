const wholeNumberFormatter = new Intl.NumberFormat("en-AU", { maximumFractionDigits: 0 });
const oneDecimalFormatter = new Intl.NumberFormat("en-AU", { maximumFractionDigits: 1 });
const currencyFormatter = new Intl.NumberFormat("en-AU", {
  style: "currency",
  currency: "AUD",
  maximumFractionDigits: 0
});

export function formatValue(value: number | null | undefined, unit?: string) {
  if (value === null || value === undefined || Number.isNaN(value)) return "No data";
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit?.startsWith("AUD")) {
    const amount = valueForUnit(value, unit);
    if (Math.abs(amount) >= 1_000_000) return formatCompactCurrency(amount);
    return currencyFormatter.format(amount);
  }
  return oneDecimalFormatter.format(value);
}

export function formatAxisValue(value: number, unit?: string) {
  if (unit === "percent") return `${Math.round(value)}%`;
  if (unit?.startsWith("AUD")) return formatCompactCurrency(valueForUnit(value, unit));
  if (Math.abs(value) >= 1_000_000) return formatCompactNumber(value);
  return oneDecimalFormatter.format(value);
}

function valueForUnit(value: number, unit?: string) {
  return unit === "AUD thousands" ? value * 1000 : value;
}

function formatCompactCurrency(value: number) {
  const sign = value < 0 ? "-" : "";
  return `${sign}$${formatCompactNumber(Math.abs(value))}`;
}

function formatCompactNumber(value: number) {
  const absValue = Math.abs(value);
  const suffixes = [
    { threshold: 1_000_000_000_000, suffix: "t" },
    { threshold: 1_000_000_000, suffix: "b" },
    { threshold: 1_000_000, suffix: "m" },
    { threshold: 1_000, suffix: "k" }
  ];
  const compactUnit = suffixes.find((item) => absValue >= item.threshold);

  if (!compactUnit) return wholeNumberFormatter.format(value);

  const scaledValue = value / compactUnit.threshold;
  const maximumFractionDigits = Math.abs(scaledValue) >= 100 ? 0 : 1;
  return `${new Intl.NumberFormat("en-AU", { maximumFractionDigits }).format(scaledValue)}${compactUnit.suffix}`;
}

export function groupBy<T>(rows: T[], key: (row: T) => string) {
  return rows.reduce<Record<string, T[]>>((acc, row) => {
    const group = key(row);
    acc[group] ||= [];
    acc[group].push(row);
    return acc;
  }, {});
}
