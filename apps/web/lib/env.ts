// Public configuration (see .env.example). NEXT_PUBLIC_* values are inlined at build time, so
// each one must be read by its full literal name.
export const env = {
  // local | development | qa | production (same values as the API's APP_ENV).
  appEnv: process.env.NEXT_PUBLIC_APP_ENV ?? "local",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://fasthyr.localhost:3000",
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://app.fasthyr.localhost:3000",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  // Shared by both hosts so one sign-in covers the site and the app (".fasthyr.com" in production).
  cookieDomain: process.env.NEXT_PUBLIC_COOKIE_DOMAIN || undefined,
};

/** Developer-only pages (the /dev/ui gallery) exist in local and development, never in QA or production. */
export const devToolsEnabled = env.appEnv === "local" || env.appEnv === "development";
