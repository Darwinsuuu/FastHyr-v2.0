import { describe, expect, it } from "vitest";

import { pageAfterResize, pageWindow } from "@/lib/pagination";

describe("pageWindow", () => {
  it("describes a middle page", () => {
    expect(pageWindow(42, 2, 10)).toEqual({
      page: 2,
      pageCount: 5,
      from: 11,
      to: 20,
      hasPrevious: true,
      hasNext: true,
    });
  });

  it("clamps pages past either end", () => {
    expect(pageWindow(42, 9, 10)).toMatchObject({ page: 5, from: 41, to: 42, hasNext: false });
    expect(pageWindow(42, 0, 10)).toMatchObject({ page: 1, from: 1, to: 10, hasPrevious: false });
  });

  it("handles an empty list", () => {
    expect(pageWindow(0, 3, 10)).toMatchObject({
      page: 1,
      pageCount: 1,
      from: 0,
      to: 0,
      hasNext: false,
    });
  });

  it("keeps the first visible row on screen when rows per page changes", () => {
    expect(pageAfterResize(3, 10, 25)).toBe(1);
    expect(pageAfterResize(3, 10, 5)).toBe(5);
  });
});
