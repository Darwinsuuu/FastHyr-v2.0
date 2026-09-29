// Manage members logic (WS-003): filters, "last active" text and the edit form's rules.

import { ApiError, type components } from "@fasthyr/api-client";

import { formatDate } from "@/lib/format";
import { type MessageKey, plural, t } from "@/lib/i18n";

export type Member = components["schemas"]["Member"];
export type Role = Member["role"];

export const ROLES: Role[] = ["admin", "recruiter", "hiring_manager"];
/** The edit dialog lists roles as the frame does: most common first. */
export const EDIT_ROLES: Role[] = ["recruiter", "hiring_manager", "admin"];

export interface MemberFilters {
  query: string;
  /** null = all roles. */
  role: Role | null;
  /** Empty = all departments. A member matches when they can see any of them. */
  departmentIds: string[];
}

export const NO_FILTERS: MemberFilters = { query: "", role: null, departmentIds: [] };

/** Search by name or email, then role and department. Admins see every department, so a
 * department filter keeps them. */
export function filterMembers(members: Member[], filters: MemberFilters): Member[] {
  const needle = filters.query.trim().toLowerCase();
  return members.filter((member) => {
    if (
      needle &&
      !(member.full_name ?? "").toLowerCase().includes(needle) &&
      !(member.email ?? "").toLowerCase().includes(needle)
    ) {
      return false;
    }
    if (filters.role && member.role !== filters.role) return false;
    if (filters.departmentIds.length && member.role !== "admin") {
      return member.departments.some((d) => filters.departmentIds.includes(d.id));
    }
    return true;
  });
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/**
 * "Now", "12 minutes ago", "2 hours ago", "Yesterday", "3 days ago", then the date. Activity is
 * recorded at most every 5 minutes, so anything newer reads as now.
 */
export function lastActiveText(
  value: string | null | undefined,
  now: Date,
  timeZone: string,
): string {
  if (!value) return t("members.lastActive.never");
  const elapsed = Math.max(0, now.getTime() - new Date(value).getTime());
  if (elapsed < 5 * MINUTE) return t("members.lastActive.now");
  if (elapsed < HOUR) return plural("members.lastActive.minutes", Math.floor(elapsed / MINUTE));
  if (elapsed < DAY) return plural("members.lastActive.hours", Math.floor(elapsed / HOUR));
  if (elapsed < 2 * DAY) return t("members.lastActive.yesterday");
  if (elapsed < 30 * DAY) return plural("members.lastActive.days", Math.floor(elapsed / DAY));
  return formatDate(value, timeZone);
}

export function displayName(member: Pick<Member, "full_name" | "email">): string {
  return member.full_name || member.email || t("members.unnamed");
}

/** "All departments" for Admins, the names for others, or "No departments yet". */
export function departmentsText(member: Pick<Member, "role" | "departments">): string {
  if (member.role === "admin") return t("members.allDepartments");
  if (!member.departments.length) return t("members.noDepartments");
  return member.departments.map((d) => d.name).join(", ");
}

/** Owners and yourself have no actions: the API refuses both (FR-WS-04). */
export function canManage(member: Pick<Member, "is_owner" | "is_you">): boolean {
  return !member.is_owner && !member.is_you;
}

/** The message for a failed save or removal. */
export function actionErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError) {
    if (error.code === "owner_access_locked") return "members.errors.owner";
    if (error.code === "own_access_locked") return "members.errors.self";
    if (error.code === "unknown_department") return "members.errors.department";
    if (error.status === 404) return "members.errors.gone";
  }
  return "members.errors.failed";
}
