// TanStack Query keys. Workspace-scoped keys start with ["ws", workspaceId] so switching
// workspace can drop them all at once.
export const keys = {
  me: () => ["me"] as const,
  myWorkspaces: () => ["me", "workspaces"] as const,
  workspace: (workspaceId: string) => ["ws", workspaceId] as const,
  departments: (workspaceId: string) => ["ws", workspaceId, "departments"] as const,
};
