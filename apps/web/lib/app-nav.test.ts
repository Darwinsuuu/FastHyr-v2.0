import { describe, expect, it } from "vitest";

import { HOME_PATH, navFor, navItemFor, switchDestination } from "./app-nav";

const hrefs = (role: Parameters<typeof navFor>[0]) =>
  navFor(role).flatMap((section) => section.items.map((item) => item.href));

describe("nav by role", () => {
  it("shows admins every item", () => {
    expect(hrefs("admin")).toEqual([
      "/getting-started",
      "/overview",
      "/pipelines",
      "/candidates",
      "/billing",
      "/billing/usage",
      "/settings/company",
      "/settings/departments",
      "/settings/members",
      "/settings/email-templates",
    ]);
  });

  it("shows recruiters credit usage and email templates, not billing or workspace settings", () => {
    expect(hrefs("recruiter")).toEqual([
      "/getting-started",
      "/overview",
      "/pipelines",
      "/candidates",
      "/billing/usage",
      "/settings/email-templates",
    ]);
  });

  it("shows hiring managers the main items only, without empty section headings", () => {
    const sections = navFor("hiring_manager");
    expect(sections).toHaveLength(1);
    expect(sections[0]?.heading).toBeNull();
    expect(hrefs("hiring_manager")).toEqual([
      "/getting-started",
      "/overview",
      "/pipelines",
      "/candidates",
    ]);
  });
});

describe("active item", () => {
  it("matches the item and its sub-pages", () => {
    expect(navItemFor("/pipelines")?.href).toBe("/pipelines");
    expect(navItemFor("/pipelines/0b6c/edit")?.href).toBe("/pipelines");
  });

  it("prefers the longest match", () => {
    expect(navItemFor("/billing")?.href).toBe("/billing");
    expect(navItemFor("/billing/usage")?.href).toBe("/billing/usage");
  });

  it("doesn't match look-alike paths", () => {
    expect(navItemFor("/pipelines-archive")).toBeNull();
    expect(navItemFor("/")).toBeNull();
  });
});

describe("switching workspace", () => {
  it("lands on the top page of the same section", () => {
    expect(switchDestination("/pipelines/0b6c", "recruiter")).toBe("/pipelines");
    expect(switchDestination("/settings/members", "admin")).toBe("/settings/members");
  });

  it("goes to Overview when the new role can't see the section", () => {
    expect(switchDestination("/billing", "recruiter")).toBe(HOME_PATH);
    expect(switchDestination("/settings/email-templates", "hiring_manager")).toBe(HOME_PATH);
    expect(switchDestination("/", "admin")).toBe(HOME_PATH);
  });
});
