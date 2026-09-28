import { siteName, tagline } from "@/lib/site";

// Placeholder home page. The real landing page is WEB-001; tokens and fonts arrive in FND-005.
export default function Home() {
  return (
    <main style={{ padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>{siteName}</h1>
      <p>{tagline}</p>
    </main>
  );
}
