import { LoginForm } from "@/app/site/login/login-form";
import { t } from "@/lib/i18n";

// Temporary sign-in so the session and API client can be tested. AUTH-001 replaces this page
// with the designed EmployerLogin screen.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { next, error } = await searchParams;
  return (
    <main className="page-gutter py-12">
      <div className="mx-auto w-full max-w-sm">
        <h1 className="type-heading">{t("auth.signInTitle")}</h1>
        <p className="type-body-sm mt-2 text-ink-muted">{t("auth.signInPlaceholderNote")}</p>
        <LoginForm next={next ?? null} failed={error === "signin"} />
      </div>
    </main>
  );
}
