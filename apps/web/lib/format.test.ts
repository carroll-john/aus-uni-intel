import { describe, expect, it } from "vitest";
import { formatAxisValue, formatValue, groupBy } from "@/lib/format";

describe("formatValue", () => {
  it("returns 'No data' for null/undefined/NaN", () => {
    expect(formatValue(null)).toBe("No data");
    expect(formatValue(undefined)).toBe("No data");
    expect(formatValue(Number.NaN)).toBe("No data");
  });

  it("formats percentages to one decimal", () => {
    expect(formatValue(76.5, "percent")).toBe("76.5%");
    expect(formatValue(80, "percent")).toBe("80.0%");
  });

  it("scales AUD thousands and compacts large values", () => {
    // 45_200 (thousands) -> 45,200,000 -> $45.2m
    expect(formatValue(45_200, "AUD thousands")).toBe("$45.2m");
    // small AUD amounts render as currency
    expect(formatValue(500, "AUD")).toBe("$500");
  });

  it("formats plain numbers with one decimal", () => {
    expect(formatValue(1234.5)).toBe("1,234.5");
  });
});

describe("formatAxisValue", () => {
  it("rounds percentages", () => {
    expect(formatAxisValue(76.6, "percent")).toBe("77%");
  });

  it("compacts large plain numbers", () => {
    expect(formatAxisValue(1_500_000)).toBe("1.5m");
  });
});

describe("groupBy", () => {
  it("groups rows by key", () => {
    const rows = [
      { group: "a", n: 1 },
      { group: "b", n: 2 },
      { group: "a", n: 3 },
    ];
    const grouped = groupBy(rows, (row) => row.group);
    expect(Object.keys(grouped).sort()).toEqual(["a", "b"]);
    expect(grouped.a).toHaveLength(2);
  });
});
