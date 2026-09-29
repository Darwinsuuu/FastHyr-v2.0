// Departments page logic (WS-002): the rows it shows, search, summary numbers and form rules.

import { ApiError, type components } from "@fasthyr/api-client";

import type { MessageKey } from "@/lib/i18n";

export type Department = components["schemas"]["Department"];
export type DepartmentStats = components["schemas"]["DepartmentStats"];
export type DepartmentList = components["schemas"]["DepartmentList"];

/** Same limits as the API: 1 to 40 characters for the name, 120 for the description. */
export const NAME_MAX = 40;
export const DESCRIPTION_MAX = 120;

export interface DepartmentRow {
  /** The department id, or null for the built-in No department. */
  id: string | null;
  name: string;
  description: string | null;
  createdAt: string | null;
  stats: DepartmentStats;
}

const EMPTY_STATS: DepartmentStats = {
  pipelines: { active: 0, scheduled: 0, closed: 0, draft: 0 },
  candidate_count: 0,
  members: [],
};

/** Every department by name, then No department last (it can't be renamed or deleted). */
export function departmentRows(list: DepartmentList, noDepartmentName: string): DepartmentRow[] {
  const rows: DepartmentRow[] = list.departments.map((department) => ({
    id: department.id,
    name: department.name,
    description: department.description ?? null,
    createdAt: department.created_at,
    stats: department.stats ?? EMPTY_STATS,
  }));
  rows.push({
    id: null,
    name: noDepartmentName,
    description: null,
    createdAt: null,
    stats: list.no_department ?? EMPTY_STATS,
  });
  return rows;
}

/** Pipelines as the Pipelines list shows them: drafts aren't listed, so they aren't counted. */
export function pipelineCount(stats: DepartmentStats): number {
  const { active, scheduled, closed } = stats.pipelines;
  return active + scheduled + closed;
}

/** Case-insensitive match on name or description. */
export function searchRows(rows: DepartmentRow[], query: string): DepartmentRow[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter(
    (row) =>
      row.name.toLowerCase().includes(needle) ||
      (row.description ?? "").toLowerCase().includes(needle),
  );
}

export interface DepartmentSummary {
  departments: number;
  pipelines: number;
  filed: number;
  noDepartment: number;
  empty: number;
}

export function summarize(list: DepartmentList): DepartmentSummary {
  const counts = list.departments.map((d) => pipelineCount(d.stats ?? EMPTY_STATS));
  const filed = counts.reduce((sum, count) => sum + count, 0);
  const noDepartment = pipelineCount(list.no_department ?? EMPTY_STATS);
  return {
    departments: list.departments.length,
    pipelines: filed + noDepartment,
    filed,
    noDepartment,
    empty: counts.filter((count) => count === 0).length,
  };
}

const collapse = (value: string) => value.trim().replace(/\s+/g, " ").toLowerCase();

/**
 * The name field's error, checked before saving: required, "No department" is built in, and
 * names are unique ignoring case. `editingId` is the department being renamed (it may keep its name).
 */
export function departmentNameError(
  name: string,
  departments: Pick<Department, "id" | "name">[],
  editingId: string | null,
): MessageKey | null {
  const value = collapse(name);
  if (!value) return "departments.form.nameRequired";
  if (value === "no department") return "departments.form.nameReserved";
  if (departments.some((d) => d.id !== editingId && collapse(d.name) === value)) {
    return "departments.form.nameTaken";
  }
  return null;
}

/** The name field's error for a failed save, or null when the failure isn't about the name. */
export function saveErrorKey(error: unknown): MessageKey | null {
  if (!(error instanceof ApiError)) return null;
  if (error.code === "department_name_taken") return "departments.form.nameTaken";
  if (error.code === "department_name_reserved") return "departments.form.nameReserved";
  return null;
}
