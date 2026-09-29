// The TA app's sidebar (DASH-001): sections, the action each page needs, and the rules the shell
// uses for the active item and for where a workspace switch lands.

import type { MessageKey } from "@/lib/i18n";
import { type Action, can, type Role } from "@/lib/permissions";

export type NavIcon =
  | "gettingStarted"
  | "overview"
  | "pipelines"
  | "candidates"
  | "billing"
  | "creditUsage"
  | "company"
  | "departments"
  | "members"
  | "emailTemplates";

export interface NavItem {
  href: string;
  label: MessageKey;
  icon: NavIcon;
  /** The permission the page needs (SECURITY.md §2); the item is hidden without it. */
  action: Action;
}

export interface NavSection {
  /** No heading for the first, unlabelled group. */
  heading: MessageKey | null;
  items: NavItem[];
}

export const NAV: NavSection[] = [
  {
    heading: null,
    items: [
      {
        href: "/getting-started",
        label: "shell.nav.gettingStarted",
        icon: "gettingStarted",
        action: "view_overview",
      },
      { href: "/overview", label: "shell.nav.overview", icon: "overview", action: "view_overview" },
      {
        href: "/pipelines",
        label: "shell.nav.pipelines",
        icon: "pipelines",
        action: "view_pipelines",
      },
      {
        href: "/candidates",
        label: "shell.nav.candidates",
        icon: "candidates",
        action: "view_candidate_pool",
      },
    ],
  },
  {
    heading: "shell.nav.billingHeading",
    items: [
      { href: "/billing", label: "shell.nav.billing", icon: "billing", action: "manage_billing" },
      {
        href: "/billing/usage",
        label: "shell.nav.creditUsage",
        icon: "creditUsage",
        action: "view_credit_usage",
      },
    ],
  },
  {
    heading: "shell.nav.adminHeading",
    items: [
      {
        href: "/settings/company",
        label: "shell.nav.company",
        icon: "company",
        action: "manage_workspace",
      },
      {
        href: "/settings/departments",
        label: "shell.nav.departments",
        icon: "departments",
        action: "manage_workspace",
      },
      {
        href: "/settings/members",
        label: "shell.nav.members",
        icon: "members",
        action: "manage_workspace",
      },
      {
        href: "/settings/email-templates",
        label: "shell.nav.emailTemplates",
        icon: "emailTemplates",
        action: "manage_email_templates",
      },
    ],
  },
];

/** Where the app opens, and where a switch lands when the current section isn't available. */
export const HOME_PATH = "/overview";

/** The sections a role sees; a section left with no items is dropped with its heading. */
export function navFor(role: Role): NavSection[] {
  return NAV.map((section) => ({
    ...section,
    items: section.items.filter((item) => can(role, item.action)),
  })).filter((section) => section.items.length > 0);
}

function within(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** The nav item a path belongs to: the longest matching href ("/billing/usage" beats "/billing"). */
export function navItemFor(pathname: string): NavItem | null {
  let match: NavItem | null = null;
  for (const item of NAV.flatMap((section) => section.items)) {
    if (within(pathname, item.href) && (!match || item.href.length > match.href.length)) {
      match = item;
    }
  }
  return match;
}

/**
 * Where to go after switching workspace: the top page of the current section (a pipeline's page
 * doesn't exist in the other workspace), or Overview if the new role can't see that section.
 */
export function switchDestination(pathname: string, role: Role): string {
  const item = navItemFor(pathname);
  return item && can(role, item.action) ? item.href : HOME_PATH;
}
