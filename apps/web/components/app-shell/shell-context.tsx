"use client";

import { createContext, useContext } from "react";

import type { Role } from "@/lib/permissions";

export interface ShellUser {
  id: string;
  name: string;
  email: string;
  avatarUrl: string | null;
}

export interface ShellWorkspace {
  id: string;
  name: string;
  role: Role;
  memberCount: number;
  /** For apply links: `/apply/{slug}/{pipeline-slug}`. */
  slug: string;
}

export interface ShellState {
  user: ShellUser;
  /** The active workspace (the `fh_ws` cookie). */
  workspace: ShellWorkspace;
  /** Every workspace the user belongs to, in API order. */
  workspaces: ShellWorkspace[];
}

export const ShellContext = createContext<ShellState | null>(null);

/** The signed-in user and active workspace, for any page inside the app shell. */
export function useShell(): ShellState {
  const state = useContext(ShellContext);
  if (!state) throw new Error("useShell() is only available inside <AppShell>.");
  return state;
}
