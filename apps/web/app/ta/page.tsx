import { MePanel } from "@/app/ta/me-panel";
import { t } from "@/lib/i18n";

// Placeholder for the app host: proves the signed-in user can call the API.
// Real app pages start with DASH-001 (app shell) and AUTH-003 (workspaces).
export default function AppHome() {
  return (
    <main className="page-gutter py-8 md:py-12">
      <h1 className="type-heading">{t("app.title")}</h1>
      <MePanel />
    </main>
  );
}
