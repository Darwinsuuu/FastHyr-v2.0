"use client";

import { ImageIcon, TrashIcon, UploadSimpleIcon } from "@phosphor-icons/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type DragEvent, type FormEvent, type ReactNode, useId, useMemo, useState } from "react";

import { useShell } from "@/components/app-shell/shell-context";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, unwrap } from "@/lib/api/client";
import { keys } from "@/lib/api/keys";
import { cn } from "@/lib/cn";
import {
  ABOUT_MAX,
  BANNER_TYPES,
  type BrandingKind,
  COMPANY_NAME_MAX,
  COMPANY_SIZES,
  type CompanyProfile,
  countryOptions,
  formErrors,
  formFromProfile,
  type ImageChange,
  INDUSTRIES,
  LOGO_TYPES,
  type ProfileForm,
  sameForm,
  saveErrorKey,
  timeZoneOptions,
  updateRequest,
  URL_MAX,
} from "@/lib/company-profile";
import { type Prepared, prepareBanner, prepareLogo } from "@/lib/company-profile/images";
import { formatNumber } from "@/lib/format";
import { type MessageKey, t } from "@/lib/i18n";

/** Company profile (frame CompanyProfile, FR-WS-01): the employer brand candidates see. */
export function CompanyProfilePage() {
  const { workspace } = useShell();
  const queryKey = keys.companyProfile(workspace.id);
  const query = useQuery({
    queryKey,
    queryFn: async () => unwrap(await api.GET("/v1/workspace/company-profile")),
    // The image previews are signed URLs that last 15 minutes.
    staleTime: 10 * 60 * 1000,
  });

  return (
    <div className="flex flex-col">
      {query.isError ? (
        <div className="page-gutter py-10 lg:px-10">
          <PageHeading />
          <div className="mt-6 rounded-lg border border-line bg-surface-raised">
            <EmptyState title={t("companyProfile.loadFailed")} />
          </div>
        </div>
      ) : query.data ? (
        <ProfileEditor key={query.data.updated_at} profile={query.data} queryKey={queryKey} />
      ) : (
        <div className="page-gutter flex flex-col gap-6 py-6 md:py-10 lg:px-10">
          <PageHeading />
          {Array.from({ length: 3 }, (_, index) => (
            <Skeleton key={index} className="h-64 w-full rounded-lg" />
          ))}
        </div>
      )}
    </div>
  );
}

function PageHeading() {
  return (
    <div className="flex max-w-[680px] flex-col gap-2">
      <p className="type-label text-evergreen uppercase">{t("companyProfile.eyebrow")}</p>
      <h1 className="type-heading">{t("companyProfile.title")}</h1>
      <p className="type-body text-ink-muted">{t("companyProfile.intro")}</p>
    </div>
  );
}

function ProfileEditor({
  profile,
  queryKey,
}: {
  profile: CompanyProfile;
  queryKey: ReturnType<typeof keys.companyProfile>;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const initial = useMemo(() => formFromProfile(profile), [profile]);
  const [form, setForm] = useState<ProfileForm>(initial);
  const [logo, setLogo] = useState<ImageChange>(null);
  const [banner, setBanner] = useState<ImageChange>(null);
  const [tried, setTried] = useState(false);
  const [saving, setSaving] = useState(false);

  const countries = useMemo(() => countryOptions(), []);
  const zones = useMemo(() => timeZoneOptions(), []);
  const errors = formErrors(form);
  const shownErrors = tried ? errors : {};
  const dirty = !sameForm(form, initial) || logo !== null || banner !== null;

  const update = (changes: Partial<ProfileForm>) =>
    setForm((current) => ({ ...current, ...changes }));
  const error = (key: keyof ProfileForm) => {
    const message = shownErrors[key];
    return message ? t(message) : undefined;
  };

  function reset() {
    setForm(initial);
    setLogo(null);
    setBanner(null);
    setTried(false);
  }

  async function uploadImage(kind: BrandingKind, file: File): Promise<string> {
    const target = unwrap(
      await api.POST("/v1/workspace/company-profile/branding-upload", { body: { kind } }),
    );
    const response = await fetch(target.url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type },
    });
    if (!response.ok) throw new Error("upload failed");
    return target.upload_id;
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (Object.keys(errors).length > 0 || !dirty) return;
    setSaving(true);
    try {
      const uploads: { logo_upload_id?: string; banner_upload_id?: string } = {};
      if (logo && logo !== "remove") uploads.logo_upload_id = await uploadImage("logo", logo.file);
      if (banner && banner !== "remove")
        uploads.banner_upload_id = await uploadImage("banner", banner.file);
      const saved = unwrap(
        await api.PUT("/v1/workspace/company-profile", {
          body: updateRequest(form, uploads, {
            logo: logo === "remove",
            banner: banner === "remove",
          }),
        }),
      );
      toast({ title: t("companyProfile.saved") });
      // A new `updated_at` remounts the editor with the saved values.
      queryClient.setQueryData(queryKey, saved);
    } catch (failure) {
      toast({ title: t(saveErrorKey(failure)), tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  const actions = (
    <>
      <Button
        variant="secondary"
        disabled={!dirty || saving}
        onClick={reset}
        className="max-sm:flex-1"
      >
        {t("companyProfile.cancel")}
      </Button>
      <Button
        type="submit"
        form="company-profile"
        loading={saving}
        disabled={!dirty}
        className="max-sm:flex-1"
      >
        {t("companyProfile.save")}
      </Button>
    </>
  );

  return (
    <>
      <header className="border-b border-line bg-surface lg:sticky lg:top-0 lg:z-10">
        <div className="page-gutter flex flex-col gap-4 py-6 md:py-8 lg:flex-row lg:items-end lg:justify-between lg:gap-8 lg:px-10 lg:py-6">
          <PageHeading />
          <div className="hidden shrink-0 gap-3 lg:flex">{actions}</div>
        </div>
      </header>

      <form
        id="company-profile"
        noValidate
        onSubmit={save}
        className="page-gutter flex flex-col gap-4 py-6 md:py-8 lg:px-10"
      >
        <Section
          title={t("companyProfile.brand.title")}
          description={t("companyProfile.brand.description")}
        >
          <Row
            label={t("companyProfile.logo.label")}
            description={t("companyProfile.logo.description")}
          >
            <ImagePicker
              kind="logo"
              currentUrl={profile.logo_url}
              change={logo}
              onChange={setLogo}
              accept={LOGO_TYPES}
              prepare={prepareLogo}
            />
          </Row>
          <Row
            label={t("companyProfile.banner.label")}
            description={t("companyProfile.banner.description")}
          >
            <ImagePicker
              kind="banner"
              currentUrl={profile.banner_url}
              change={banner}
              onChange={setBanner}
              accept={BANNER_TYPES}
              prepare={prepareBanner}
            />
            <p className="mt-2 text-[13px] leading-[18px] text-ink-muted">
              {t("companyProfile.banner.fallback")}
            </p>
          </Row>
          <Row
            label={t("companyProfile.name.label")}
            description={t("companyProfile.name.description")}
            fieldLabel
          >
            <Field
              label={t("companyProfile.name.label")}
              hideLabel
              required
              error={error("company_name")}
            >
              <Input
                value={form.company_name}
                maxLength={COMPANY_NAME_MAX}
                autoComplete="organization"
                placeholder={t("companyProfile.name.placeholder")}
                onChange={(event) => update({ company_name: event.target.value })}
              />
            </Field>
          </Row>
          <Row
            label={t("companyProfile.website.label")}
            description={t("companyProfile.website.description")}
            fieldLabel
          >
            <Field label={t("companyProfile.website.label")} hideLabel error={error("website")}>
              <PrefixedInput
                prefix="https://"
                value={form.website}
                maxLength={URL_MAX}
                inputMode="url"
                autoComplete="url"
                placeholder={t("companyProfile.website.placeholder")}
                onChange={(website) => update({ website })}
              />
            </Field>
          </Row>
        </Section>

        <Section
          title={t("companyProfile.details.title")}
          description={t("companyProfile.details.description")}
        >
          <div className="grid gap-5 border-t border-line pt-5 sm:grid-cols-2">
            <Field label={t("companyProfile.industry.label")}>
              <Select
                value={form.industry}
                placeholder={t("companyProfile.industry.placeholder")}
                options={INDUSTRIES.map((value) => ({
                  value,
                  label: t(`companyProfile.industry.options.${value}`),
                }))}
                onValueChange={(industry) => update({ industry })}
              />
            </Field>
            <Field label={t("companyProfile.size.label")}>
              <Select
                value={form.company_size}
                placeholder={t("companyProfile.size.placeholder")}
                options={COMPANY_SIZES.map((value) => ({
                  value,
                  label: t(`companyProfile.size.options.${value}`),
                }))}
                onValueChange={(company_size) => update({ company_size })}
              />
            </Field>
            <Field label={t("companyProfile.country.label")}>
              <Select
                value={form.hq_country}
                placeholder={t("companyProfile.country.placeholder")}
                options={countries}
                onValueChange={(hq_country) => update({ hq_country })}
              />
            </Field>
            <Field
              label={t("companyProfile.timezone.label")}
              hint={t("companyProfile.timezone.hint")}
            >
              <Select
                value={form.timezone}
                placeholder={t("companyProfile.timezone.placeholder")}
                options={zones}
                onValueChange={(timezone) => update({ timezone })}
              />
            </Field>
          </div>
        </Section>

        <Section
          title={t("companyProfile.candidates.title")}
          description={t("companyProfile.candidates.description")}
        >
          <div className="flex flex-col gap-5 border-t border-line pt-5">
            <AboutField value={form.about} onChange={(about) => update({ about })} />
            <Field
              label={t("companyProfile.careers.label")}
              hint={t("companyProfile.careers.hint")}
              error={error("careers_url")}
            >
              <Input
                type="url"
                inputMode="url"
                value={form.careers_url}
                maxLength={URL_MAX}
                placeholder={t("companyProfile.careers.placeholder")}
                onChange={(event) => update({ careers_url: event.target.value })}
              />
            </Field>
          </div>
        </Section>
      </form>

      <footer className="sticky bottom-0 z-20 border-t border-line bg-surface-raised safe-bottom lg:hidden">
        <div className="page-gutter flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
          <p aria-live="polite" className="text-[13px] leading-[18px] text-ink-muted">
            {dirty ? t("companyProfile.unsaved") : ""}
          </p>
          <div className="flex gap-3">{actions}</div>
        </div>
      </footer>
    </>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <section
      aria-labelledby={id}
      className="flex flex-col gap-5 rounded-lg border border-line bg-surface-raised p-4 sm:p-6"
    >
      <div className="flex flex-col gap-1">
        <h2 id={id} className="text-[18px] leading-6 font-[650] text-ink">
          {title}
        </h2>
        <p className="text-[14px] leading-5 text-ink-muted">{description}</p>
      </div>
      {children}
    </section>
  );
}

/** A label column beside the control from `md` (frame CompanyProfile, Brand section). */
function Row({
  label,
  description,
  fieldLabel,
  children,
}: {
  label: string;
  description: string;
  /** The control has its own (visually hidden) label; this column is then decoration. */
  fieldLabel?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-t border-line pt-5 md:flex-row md:gap-8">
      <div
        className="flex flex-col gap-1 md:w-[240px] md:shrink-0"
        aria-hidden={fieldLabel || undefined}
      >
        <span className="text-[14px] leading-5 font-semibold text-ink">{label}</span>
        <span className="text-[13px] leading-[18px] text-ink-muted">{description}</span>
      </div>
      <div className="min-w-0 flex-1 md:max-w-[520px]">{children}</div>
    </div>
  );
}

function PrefixedInput({
  prefix,
  value,
  onChange,
  ...props
}: {
  prefix: string;
  value: string;
  onChange: (value: string) => void;
  maxLength: number;
  inputMode: "url";
  autoComplete: string;
  placeholder: string;
}) {
  return (
    <div className="flex h-12 overflow-hidden rounded-[6px] border border-line-strong bg-surface-raised has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus has-aria-invalid:border-signal-gap">
      <span
        aria-hidden="true"
        className="flex items-center border-r border-line bg-surface-sunk px-3 text-[15px] text-ink-muted"
      >
        {prefix}
      </span>
      <Input
        {...props}
        value={value}
        // Pasting a full address drops the duplicate prefix.
        onChange={(event) => onChange(event.target.value.replace(/^https:\/\//i, ""))}
        className="h-full min-w-0 flex-1 rounded-none border-0 focus-visible:outline-none"
      />
    </div>
  );
}

function AboutField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const id = useId();
  return (
    <Field label={t("companyProfile.about.label")}>
      <Textarea
        rows={5}
        value={value}
        maxLength={ABOUT_MAX}
        placeholder={t("companyProfile.about.placeholder")}
        aria-describedby={`${id}-hint ${id}-count`}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="flex items-start justify-between gap-4 text-[13px] leading-[18px]">
        <p id={`${id}-hint`} className="text-ink-muted">
          {t("companyProfile.about.hint")}
        </p>
        <span
          id={`${id}-count`}
          className={cn(
            "shrink-0 tabular-nums",
            value.length >= ABOUT_MAX ? "font-semibold text-signal-gap" : "text-ink-muted",
          )}
        >
          {t("companyProfile.about.count", {
            count: formatNumber(value.length),
            max: formatNumber(ABOUT_MAX),
          })}
        </span>
      </div>
    </Field>
  );
}

function ImagePicker({
  kind,
  currentUrl,
  change,
  onChange,
  accept,
  prepare,
}: {
  kind: BrandingKind;
  currentUrl: string | null;
  change: ImageChange;
  onChange: (change: ImageChange) => void;
  accept: string[];
  prepare: (file: File) => Promise<Prepared>;
}) {
  const inputId = useId();
  const [problem, setProblem] = useState<MessageKey | null>(null);
  const [dragging, setDragging] = useState(false);
  const preview = previewOf(change, currentUrl);
  const copy = (
    key: "label" | "hint" | "alt" | "choose" | "replace" | "remove" | "willRemove" | "undo",
  ) => t(`companyProfile.${kind}.${key}`);

  function choose(next: ImageChange) {
    if (change && change !== "remove") URL.revokeObjectURL(change.previewUrl);
    onChange(next);
  }

  async function take(file: File | undefined) {
    if (!file) return;
    const result = await prepare(file);
    if ("error" in result) {
      setProblem(result.error);
      return;
    }
    setProblem(null);
    choose({ file: result.file, previewUrl: URL.createObjectURL(result.file) });
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    void take(event.dataTransfer.files[0]);
  }

  const hasImage = preview !== null;
  const square = kind === "logo";

  const fileInput = (
    <input
      id={inputId}
      type="file"
      accept={accept.join(",")}
      aria-label={hasImage ? copy("replace") : copy("choose")}
      aria-describedby={problem ? `${inputId}-error` : `${inputId}-hint`}
      className="sr-only"
      onChange={(event) => {
        void take(event.target.files?.[0]);
        event.target.value = "";
      }}
    />
  );

  return (
    <div className="flex flex-col gap-2">
      {hasImage ? (
        <div className={cn("flex gap-4", square ? "items-center" : "flex-col")}>
          {/* eslint-disable-next-line @next/next/no-img-element -- signed or local URLs */}
          <img
            src={preview}
            alt={copy("alt")}
            className={cn(
              "rounded-md border border-line bg-surface-sunk",
              square ? "size-20 shrink-0 object-contain" : "aspect-[3/1] w-full object-cover",
            )}
          />
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <label
                htmlFor={inputId}
                onDragOver={(event) => event.preventDefault()}
                onDrop={onDrop}
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-line-strong bg-surface-raised px-4 text-[15px] font-semibold text-ink transition-colors duration-200 ease-out hover:border-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus"
              >
                <UploadSimpleIcon aria-hidden="true" className="size-5" />
                {copy("replace")}
                {fileInput}
              </label>
              <Button
                variant="quiet"
                destructive
                icon={<TrashIcon aria-hidden="true" />}
                onClick={() => choose(change !== null ? null : "remove")}
              >
                {change !== null ? t("companyProfile.upload.discard") : copy("remove")}
              </Button>
            </div>
            <p id={`${inputId}-hint`} className="text-[12px] leading-4 text-ink-muted">
              {change !== null ? t("companyProfile.upload.dropped") : copy("hint")}
            </p>
          </div>
        </div>
      ) : (
        <div className={cn("flex gap-4", square ? "items-start" : "flex-col")}>
          {square && (
            <div className="flex size-16 shrink-0 items-center justify-center rounded-md border border-line bg-surface-sunk">
              <ImageIcon aria-hidden="true" className="size-6 text-ink-muted" />
            </div>
          )}
          <label
            htmlFor={inputId}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={cn(
              "flex min-w-0 flex-1 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-[1.5px] border-dashed border-line-strong bg-surface-raised px-4 py-5 text-center",
              "transition-colors duration-200 ease-out hover:border-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-focus",
              !square && "aspect-[3/1] min-h-36",
              dragging && "border-evergreen bg-evergreen-soft",
              problem && "border-signal-gap",
            )}
          >
            <span className="flex size-10 items-center justify-center rounded-full bg-surface-sunk text-evergreen">
              <UploadSimpleIcon aria-hidden="true" className="size-5" />
            </span>
            <span className="text-[14px] text-ink-muted">
              <span className="font-semibold text-evergreen">
                {t("companyProfile.upload.click")}
              </span>{" "}
              <span className="max-sm:hidden">{t("companyProfile.upload.drag")}</span>
            </span>
            <span id={`${inputId}-hint`} className="text-[12px] leading-4 text-ink-muted">
              {copy("hint")}
            </span>
            {fileInput}
          </label>
        </div>
      )}

      {problem && (
        <p
          id={`${inputId}-error`}
          role="alert"
          className="text-[13px] leading-[18px] font-semibold text-signal-gap"
        >
          {t(problem)}
        </p>
      )}
      {change === "remove" && (
        <p className="flex flex-wrap items-center gap-x-2 text-[13px] leading-[18px] text-ink-muted">
          {copy("willRemove")}
          <Button variant="quiet" size="sm" onClick={() => choose(null)}>
            {copy("undo")}
          </Button>
        </p>
      )}
    </div>
  );
}

/** The image to show: the new file, nothing when it's being removed, else the saved one. */
function previewOf(change: ImageChange, currentUrl: string | null): string | null {
  if (change === "remove") return null;
  return change ? change.previewUrl : currentUrl;
}
