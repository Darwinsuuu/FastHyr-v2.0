"use client";

import { InfoIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import Link from "next/link";

import { ItemListField } from "@/components/pipelines/item-list-field";
import { WizardNote } from "@/components/pipelines/wizard-note";
import { Checkbox } from "@/components/ui/checkbox";
import { ChipInput } from "@/components/ui/chip-input";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/cn";
import { t } from "@/lib/i18n";
import {
  type DepartmentOption,
  EMPLOYMENT_TYPES,
  type EmploymentType,
  JD_MAX,
  joinWithOr,
  LOCATION_MAX,
  MAX_ITEMS,
  NO_DEPARTMENT,
  OPEN_TO,
  TITLE_MAX,
  type WizardForm,
  WORK_SETUPS,
} from "@/lib/pipelines/wizard";

export interface StepProps {
  form: WizardForm;
  update: (changes: Partial<WizardForm>) => void;
  /** Someone pressed Continue while this step was blocked. */
  tried: boolean;
}

/** Step 1, Role (frame NewPipeline step 1 + A-01). */
export function RoleStep({
  form,
  update,
  tried,
  departments,
  isAdmin,
}: StepProps & { departments: DepartmentOption[]; isAdmin: boolean }) {
  const openToShort = OPEN_TO.filter((id) => form.open_to.includes(id)).map((id) =>
    t(`pipelines.wizard.role.openToOptions.${id}.short`),
  );

  return (
    <div className="flex flex-col gap-7">
      <Field label={t("pipelines.wizard.role.title")}>
        <Input
          value={form.title}
          maxLength={TITLE_MAX}
          placeholder={t("pipelines.wizard.role.titlePlaceholder")}
          onChange={(event) => update({ title: event.target.value })}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field
          label={t("pipelines.wizard.role.department")}
          hint={
            isAdmin ? (
              <>
                {t("pipelines.wizard.role.departmentHint")}{" "}
                <Link
                  href="/settings/departments"
                  className="font-semibold text-evergreen underline underline-offset-2"
                >
                  {t("pipelines.wizard.role.manageDepartments")}
                </Link>
              </>
            ) : (
              t("pipelines.wizard.role.departmentHintRecruiter")
            )
          }
          error={departments.length === 0 ? t("pipelines.wizard.role.noDepartments") : undefined}
        >
          <Select
            options={departments}
            value={form.department_id ?? (isAdmin ? NO_DEPARTMENT : undefined)}
            disabled={departments.length === 0}
            onValueChange={(value) =>
              update({ department_id: value === NO_DEPARTMENT ? null : value })
            }
          />
        </Field>
        <Field label={t("pipelines.wizard.role.employmentType")}>
          <Select
            options={EMPLOYMENT_TYPES.map((value) => ({
              value,
              label: t(`pipelines.wizard.role.employmentTypes.${value}`),
            }))}
            value={form.employment_type}
            onValueChange={(value) => update({ employment_type: value as EmploymentType })}
          />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <span className="text-[14px] leading-5 font-semibold text-ink">
            {t("pipelines.wizard.role.workSetup")}
          </span>
          <SegmentedControl
            label={t("pipelines.wizard.role.workSetup")}
            options={WORK_SETUPS.map((value) => ({
              value,
              label: t(`pipelines.wizard.role.workSetups.${value}`),
            }))}
            value={form.work_setup}
            onValueChange={(work_setup) => update({ work_setup })}
            fullWidth
          />
        </div>
        <Field label={t("pipelines.wizard.role.location")}>
          <Input
            value={form.location}
            maxLength={LOCATION_MAX}
            placeholder={t("pipelines.wizard.role.locationPlaceholder")}
            onChange={(event) => update({ location: event.target.value })}
          />
        </Field>
      </div>

      <Field label={t("pipelines.wizard.role.jd")} hint={t("pipelines.wizard.role.jdHint")}>
        <Textarea
          rows={7}
          value={form.jd_text}
          maxLength={JD_MAX}
          placeholder={t("pipelines.wizard.role.jdPlaceholder")}
          onChange={(event) => update({ jd_text: event.target.value })}
        />
      </Field>

      <ItemListField
        label={t("pipelines.wizard.role.mustHaves")}
        hint={t("pipelines.wizard.role.mustHavesHint")}
        placeholder={t("pipelines.wizard.role.mustHavesPlaceholder")}
        value={form.must_haves}
        onValueChange={(must_haves) => update({ must_haves })}
        tried={tried}
        error={t("pipelines.wizard.blocked.mustHaves")}
      >
        <WizardNote icon={<ShieldCheckIcon aria-hidden="true" />}>
          {t("pipelines.wizard.role.fairness")}
        </WizardNote>
      </ItemListField>

      <Field
        label={
          <>
            {t("pipelines.wizard.role.niceToHaves")}{" "}
            <span className="font-normal text-ink-muted">
              {t("pipelines.wizard.role.optional")}
            </span>
          </>
        }
        hint={t("pipelines.wizard.role.niceToHavesHint")}
      >
        <ChipInput
          value={form.nice_to_haves}
          onValueChange={(nice_to_haves) => update({ nice_to_haves })}
          placeholder={t("pipelines.wizard.role.niceToHavesPlaceholder")}
          max={MAX_ITEMS}
        />
      </Field>

      <Field
        label={
          <span className="flex items-center justify-between gap-3">
            <span>{t("pipelines.wizard.role.passBar")}</span>
            <span className="text-[14px] font-semibold text-ink tabular-nums">
              {t("pipelines.wizard.role.passBarValue", { value: form.resume_pass_bar })}
            </span>
          </span>
        }
        hint={t("pipelines.wizard.role.passBarHint")}
      >
        <Slider
          aria-label={t("pipelines.wizard.role.passBar")}
          value={form.resume_pass_bar}
          min={0}
          max={100}
          step={5}
          formatValue={(value) => t("pipelines.wizard.role.passBarValue", { value })}
          onValueChange={(resume_pass_bar) => update({ resume_pass_bar })}
        />
      </Field>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1.5 flex flex-col gap-1">
          <span className="text-[14px] leading-5 font-semibold text-ink">
            {t("pipelines.wizard.role.openTo")}{" "}
            <span className="font-normal text-ink-muted">
              {t("pipelines.wizard.role.optional")}
            </span>
          </span>
          <span className="text-[13px] leading-[18px] text-ink-muted">
            {t("pipelines.wizard.role.openToHint")}
          </span>
        </legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {OPEN_TO.map((id) => {
            const on = form.open_to.includes(id);
            return (
              <Checkbox
                key={id}
                label={
                  <span className="font-[650]">
                    {t(`pipelines.wizard.role.openToOptions.${id}.label`)}
                  </span>
                }
                description={t(`pipelines.wizard.role.openToOptions.${id}.description`)}
                checked={on}
                onCheckedChange={(checked) =>
                  update({
                    open_to: checked
                      ? OPEN_TO.filter((item) => item === id || form.open_to.includes(item))
                      : form.open_to.filter((item) => item !== id),
                  })
                }
                className={cn(
                  "rounded-md border px-3.5 py-3 transition-colors duration-200 ease-out",
                  on ? "border-evergreen bg-surface ring-1 ring-evergreen" : "border-line",
                )}
              />
            );
          })}
        </div>
        {openToShort.length > 0 && (
          <WizardNote icon={<InfoIcon aria-hidden="true" />}>
            {t("pipelines.wizard.role.openToNote", {
              list: joinWithOr(openToShort, t("pipelines.wizard.role.or")),
            })}
          </WizardNote>
        )}
      </fieldset>
    </div>
  );
}
