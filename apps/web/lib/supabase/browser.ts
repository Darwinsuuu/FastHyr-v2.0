"use client";

import { createBrowserClient } from "@supabase/ssr";

import { env } from "@/lib/env";
import { supabaseCookieOptions } from "@/lib/supabase/cookies";

// Auth only: the web app never reads Supabase tables (AGENTS.md hard rule 3).
export function supabaseBrowser() {
  return createBrowserClient(env.supabaseUrl, env.supabaseAnonKey, {
    cookieOptions: supabaseCookieOptions,
  });
}
