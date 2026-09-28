import { t } from "@/lib/i18n";

// Placeholder for the public site. The landing page is WEB-001.
export default function SiteHome() {
  return (
    <main className="page-gutter py-12 md:py-16">
      <p className="type-label text-ink-muted">{t("site.name")}</p>
      <h1 className="type-display-lg mt-4 md:type-display-xl">{t("site.tagline")}</h1>
      <p className="type-body mt-6 max-w-prose text-ink-muted">{t("site.placeholder")}</p>
    </main>
  );
}
