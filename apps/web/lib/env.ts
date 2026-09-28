// Public configuration (see .env.example). NEXT_PUBLIC_* values are inlined at build time, so
// each one must be read by its full literal name.
export const env = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://fasthyr.localhost:3000",
  appUrl: process.env.NEXT_PUBLIC_APP_URL ?? "http://app.fasthyr.localhost:3000",
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  // Shared by both hosts so one sign-in covers the site and the app (".fasthyr.com" in production).
  cookieDomain: process.env.NEXT_PUBLIC_COOKIE_DOMAIN || undefined,
};
