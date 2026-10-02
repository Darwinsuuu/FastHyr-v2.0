import type { PublicPipeline } from "@/lib/apply";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";

/** The employer's logo, or its initial on evergreen when there's none (frame Apply). */
export function CompanyMark({
  company,
  size,
}: {
  company: PublicPipeline["company"];
  size: "sm" | "lg";
}) {
  const box =
    size === "sm" ? "size-9 rounded-[10px] text-[18px]" : "size-12 rounded-md text-[22px]";
  if (company.logo_url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- the API's long-lived branding image
      <img
        src={company.logo_url}
        alt={t("apply.company.logoAlt", { company: company.name })}
        className={cn(box, "shrink-0 border border-line bg-surface-raised object-contain")}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        box,
        "flex shrink-0 items-center justify-center bg-evergreen font-display font-semibold text-on-evergreen",
      )}
    >
      {company.name.trim().charAt(0).toUpperCase()}
    </span>
  );
}
