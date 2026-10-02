import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  type DepartmentList,
  departmentNameError,
  departmentRows,
  saveErrorKey,
  searchRows,
  summarize,
} from "@/lib/departments";

const stats = (active: number, scheduled = 0, closed = 0, draft = 0) => ({
  pipelines: { active, scheduled, closed, draft },
  candidate_count: 0,
  members: [],
});

const LIST: DepartmentList = {
  departments: [
    {
      id: "eng",
      name: "Engineering",
      description: "Platform and QA",
      created_at: "2026-09-29T00:00:00Z",
      assigned: true,
      stats: stats(4, 0, 2, 3),
    },
    {
      id: "ops",
      name: "Operations",
      description: null,
      created_at: "2026-09-29T00:00:00Z",
      assigned: true,
      stats: stats(0, 0, 0, 1),
    },
  ],
  no_department: stats(1),
};

describe("departments", () => {
  it("lists No department last", () => {
    const rows = departmentRows(LIST, "No department");
    expect(rows.map((row) => row.id)).toEqual(["eng", "ops", null]);
  });

  it("summarises pipelines without counting drafts", () => {
    expect(summarize(LIST)).toEqual({
      departments: 2,
      pipelines: 7,
      filed: 6,
      noDepartment: 1,
      empty: 1,
    });
  });

  it("searches names and descriptions ignoring case", () => {
    const rows = departmentRows(LIST, "No department");
    expect(searchRows(rows, " QA ").map((row) => row.id)).toEqual(["eng"]);
    expect(searchRows(rows, "no dep").map((row) => row.id)).toEqual([null]);
    expect(searchRows(rows, "")).toHaveLength(3);
  });

  it("checks names like the API", () => {
    const departments = LIST.departments;
    expect(departmentNameError("  ", departments, null)).toBe("departments.form.nameRequired");
    expect(departmentNameError(" no  Department", departments, null)).toBe(
      "departments.form.nameReserved",
    );
    expect(departmentNameError("engineering", departments, null)).toBe(
      "departments.form.nameTaken",
    );
    // Renaming a department to itself in another case is fine.
    expect(departmentNameError("ENGINEERING", departments, "eng")).toBeNull();
    expect(departmentNameError("Sales", departments, null)).toBeNull();
  });

  it("maps API name errors to field copy", () => {
    expect(saveErrorKey(new ApiError(409, "department_name_taken", "Taken"))).toBe(
      "departments.form.nameTaken",
    );
    expect(saveErrorKey(new ApiError(500, "internal_error", "Oops"))).toBeNull();
  });
});
