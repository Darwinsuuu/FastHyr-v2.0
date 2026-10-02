import { TurnMark } from "@/components/brand/turn-mark";
import { t } from "@/lib/i18n";

// Drafts, cancelled pipelines and mistyped links (WORKFLOW.md §2).
export default function ApplyNotFound() {
  return (
    <main className="page-gutter flex min-h-dvh flex-col items-start justify-center gap-4 py-16">
      <TurnMark size={40} />
      <h1 className="type-display-lg">{t("apply.notFound.title")}</h1>
      <p className="type-body max-w-prose text-ink-muted">{t("apply.notFound.body")}</p>
    </main>
  );
}
