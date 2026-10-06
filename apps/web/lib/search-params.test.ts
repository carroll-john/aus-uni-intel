import { describe, expect, it } from "vitest";
import { distinct, many, one, pickOption } from "@/lib/search-params";

describe("one", () => {
  it("returns the first entry of an array or the value itself", () => {
    expect(one("a")).toBe("a");
    expect(one(["a", "b"])).toBe("a");
    expect(one(undefined)).toBeUndefined();
  });
});

describe("many", () => {
  it("splits comma strings and falls back when empty", () => {
    expect(many("a,b,c", ["x"])).toEqual(["a", "b", "c"]);
    expect(many(undefined, ["x", "y"])).toEqual(["x", "y"]);
    expect(many(["a,b", "c"], [])).toEqual(["a", "b", "c"]);
  });
});

describe("pickOption", () => {
  it("returns the value only when allowed", () => {
    expect(pickOption("VIC", ["NSW", "VIC"])).toBe("VIC");
    expect(pickOption("QLD", ["NSW", "VIC"])).toBeUndefined();
    expect(pickOption(undefined, ["NSW"])).toBeUndefined();
  });
});

describe("distinct", () => {
  it("removes falsy values and sorts uniques", () => {
    expect(distinct(["b", "a", null, "a", undefined, ""])).toEqual(["a", "b"]);
  });
});
