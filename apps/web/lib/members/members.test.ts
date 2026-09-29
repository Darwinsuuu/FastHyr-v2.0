import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  actionErrorKey,
  canManage,
  departmentsText,
  filterMembers,
  lastActiveText,
  type Member,
  NO_FILTERS,
} from "./index";

function member(overrides: Partial<Member>): Member {
  return {
    id: "m1",
    user_id: "u1",
    full_name: "Maria Santos",
    email: "maria@company.com",
    avatar_url: null,
    role: "recruiter",
    is_owner: false,
    is_you: false,
    departments: [],
    last_active_at: null,
    status: "active",
    joined_at: "2026-09-01T00:00:00Z",
    ...overrides,
  };
}

const ENG = { id: "d-eng", name: "Engineering" };
const DESIGN = { id: "d-design", name: "Design" };

const MEMBERS = [
  member({ id: "owner", full_name: "Darwin Labiste", role: "admin", is_owner: true }),
  member({ id: "maria", departments: [ENG, DESIGN] }),
  member({
    id: "jomar",
    full_name: "Jomar Reyes",
    email: "jomar@company.com",
    role: "hiring_manager",
    departments: [ENG],
  }),
  member({ id: "angela", full_name: "Angela Cruz", email: "angela@agency.com", departments: [] }),
];

const ids = (members: Member[]) => members.map((m) => m.id);

describe("filterMembers", () => {
  it("searches names and emails, ignoring case", () => {
    expect(ids(filterMembers(MEMBERS, { ...NO_FILTERS, query: " REYES " }))).toEqual(["jomar"]);
    expect(ids(filterMembers(MEMBERS, { ...NO_FILTERS, query: "agency" }))).toEqual(["angela"]);
  });

  it("filters by role", () => {
    expect(ids(filterMembers(MEMBERS, { ...NO_FILTERS, role: "recruiter" }))).toEqual([
      "maria",
      "angela",
    ]);
  });

  it("keeps members who see any chosen department, and Admins, who see them all", () => {
    expect(ids(filterMembers(MEMBERS, { ...NO_FILTERS, departmentIds: ["d-design"] }))).toEqual([
      "owner",
      "maria",
    ]);
    expect(
      ids(filterMembers(MEMBERS, { query: "", role: "hiring_manager", departmentIds: ["d-eng"] })),
    ).toEqual(["jomar"]);
  });
});

describe("lastActiveText", () => {
  const now = new Date("2026-09-29T12:00:00Z");
  const ago = (ms: number) => new Date(now.getTime() - ms).toISOString();
  const MIN = 60_000;

  it("reads as a relative time, then a date", () => {
    expect(lastActiveText(null, now, "UTC")).toBe("Not yet");
    expect(lastActiveText(ago(4 * MIN), now, "UTC")).toBe("Now");
    expect(lastActiveText(ago(12 * MIN), now, "UTC")).toBe("12 minutes ago");
    expect(lastActiveText(ago(60 * MIN), now, "UTC")).toBe("1 hour ago");
    expect(lastActiveText(ago(30 * 60 * MIN), now, "UTC")).toBe("Yesterday");
    expect(lastActiveText(ago(3 * 24 * 60 * MIN), now, "UTC")).toBe("3 days ago");
    expect(lastActiveText("2026-07-01T09:00:00Z", now, "UTC")).toMatch(/2026/);
  });
});

describe("member rules", () => {
  it("shows every department for Admins", () => {
    expect(departmentsText(MEMBERS[0]!)).toBe("All departments");
    expect(departmentsText(MEMBERS[1]!)).toBe("Engineering, Design");
    expect(departmentsText(MEMBERS[3]!)).toBe("No departments yet");
  });

  it("locks the owner and yourself", () => {
    expect(canManage(MEMBERS[0]!)).toBe(false);
    expect(canManage(member({ is_you: true }))).toBe(false);
    expect(canManage(MEMBERS[1]!)).toBe(true);
  });

  it("maps API errors to messages", () => {
    expect(actionErrorKey(new ApiError(409, "owner_access_locked", "x"))).toBe(
      "members.errors.owner",
    );
    expect(actionErrorKey(new ApiError(404, "not_found", "x"))).toBe("members.errors.gone");
    expect(actionErrorKey(new Error("offline"))).toBe("members.errors.failed");
  });
});
