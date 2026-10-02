"use client";

import { InfoIcon, MicrophoneIcon, VideoCameraIcon } from "@phosphor-icons/react";

import { ItemListField } from "@/components/pipelines/item-list-field";
import type { StepProps } from "@/components/pipelines/wizard-role-step";
import { WizardNote } from "@/components/pipelines/wizard-note";
import { ChoiceCards } from "@/components/ui/choice-cards";
import { Field } from "@/components/ui/field";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Select } from "@/components/ui/select";
import { Toggle } from "@/components/ui/toggle";
import { t } from "@/lib/i18n";
import {
  FORMATS,
  LINK_EXPIRY_DAYS,
  type LinkExpiryDays,
  SENIORITIES,
  TONES,
} from "@/lib/pipelines/wizard";

const FORMAT_ICONS = {
  video_voice: <VideoCameraIcon />,
  voice_only: <MicrophoneIcon />,
};

function GroupLabel({ children }: { children: string }) {
  return <span className="text-[14px] leading-5 font-semibold text-ink">{children}</span>;
}

/** Step 2, AI interview (frame NewPipeline step 2). */
export function InterviewStep({ form, update, tried }: StepProps) {
  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-1.5">
        <GroupLabel>{t("pipelines.wizard.interview.format")}</GroupLabel>
        <ChoiceCards
          label={t("pipelines.wizard.interview.format")}
          options={FORMATS.map((value) => ({
            value,
            label: t(`pipelines.wizard.interview.formats.${value}.label`),
            description: t(`pipelines.wizard.interview.formats.${value}.description`),
            icon: FORMAT_ICONS[value],
          }))}
          value={form.interview_format}
          onValueChange={(interview_format) => update({ interview_format })}
        />
      </div>

      <WizardNote icon={<InfoIcon aria-hidden="true" />}>
        <strong className="font-[650]">{t("pipelines.wizard.interview.adaptiveTitle")}</strong>{" "}
        {t("pipelines.wizard.interview.adaptiveBody")}
      </WizardNote>

      <div className="flex flex-col gap-1.5">
        <GroupLabel>{t("pipelines.wizard.interview.tone")}</GroupLabel>
        <ChoiceCards
          label={t("pipelines.wizard.interview.tone")}
          columns={3}
          options={TONES.map((value) => ({
            value,
            label: t(`pipelines.wizard.interview.tones.${value}.label`),
            description: t(`pipelines.wizard.interview.tones.${value}.description`),
          }))}
          value={form.tone}
          onValueChange={(tone) => update({ tone })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <GroupLabel>{t("pipelines.wizard.interview.seniority")}</GroupLabel>
        <SegmentedControl
          label={t("pipelines.wizard.interview.seniority")}
          options={SENIORITIES.map((value) => ({
            value,
            label: t(`pipelines.wizard.interview.seniorities.${value}`),
          }))}
          value={form.seniority}
          onValueChange={(seniority) => update({ seniority })}
          fullWidth
          className="sm:w-auto"
        />
      </div>

      <ItemListField
        label={t("pipelines.wizard.interview.skills")}
        hint={t("pipelines.wizard.interview.skillsHint")}
        placeholder={t("pipelines.wizard.interview.skillsPlaceholder")}
        value={form.skills_to_probe}
        onValueChange={(skills_to_probe) => update({ skills_to_probe })}
        tried={tried}
        error={t("pipelines.wizard.blocked.skills")}
      />

      <section className="flex flex-col gap-3 rounded-md border border-line p-4 md:p-5">
        <h3 className="text-[15px] leading-5 font-[650] text-ink">
          {t("pipelines.wizard.interview.linkHeading")}
        </h3>
        <Field label={t("pipelines.wizard.interview.expiry")} className="sm:max-w-60">
          <Select
            options={LINK_EXPIRY_DAYS.map((days) => ({
              value: String(days),
              label: t("pipelines.wizard.interview.expiryDays", { days }),
            }))}
            value={String(form.link_expiry_days)}
            onValueChange={(value) => update({ link_expiry_days: Number(value) as LinkExpiryDays })}
          />
        </Field>
        <div className="flex flex-col divide-y divide-line">
          <Toggle
            label={t("pipelines.wizard.interview.reminder")}
            description={t("pipelines.wizard.interview.reminderHint")}
            checked={form.reminder_enabled}
            onCheckedChange={(reminder_enabled) => update({ reminder_enabled })}
          />
          <Toggle
            label={t("pipelines.wizard.interview.integrity")}
            description={t("pipelines.wizard.interview.integrityHint")}
            checked={form.integrity_enabled}
            onCheckedChange={(integrity_enabled) => update({ integrity_enabled })}
          />
        </div>
      </section>
    </div>
  );
}
