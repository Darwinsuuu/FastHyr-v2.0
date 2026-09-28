"use client";

import { createApiClient } from "@fasthyr/api-client";

import { env } from "@/lib/env";
import { supabaseBrowser } from "@/lib/supabase/browser";
import { readWorkspaceId } from "@/lib/workspace";

export { ApiError, unwrap } from "@fasthyr/api-client";

// The browser's API client: every call carries the signed-in user's access token and the
// active workspace. Only use this for business data; never fetch endpoints by hand.
export const api = createApiClient({
  baseUrl: env.apiUrl,
  getAccessToken: async () => {
    const { data } = await supabaseBrowser().auth.getSession();
    return data.session?.access_token ?? null;
  },
  getWorkspaceId: () => readWorkspaceId(document.cookie),
});
