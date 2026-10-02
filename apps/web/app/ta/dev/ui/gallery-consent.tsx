"use client";

import { useState } from "react";

import { ConsentCheckbox } from "@/components/consent/consent-checkbox";
import { Button } from "@/components/ui/button";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { Skeleton } from "@/components/ui/skeleton";
import { t } from "@/lib/i18n";
import { useNotices } from "@/lib/notices/use-notices";

import { Row, Section } from "./gallery-parts";

// Developer-only: the live notice texts from the API (COMP-002) in each consent spot.

type Format = "video_voice" | "voice_only";

export function ConsentSection() {
  const notices = useNotices();
  const [format, setFormat] = useState<Format>("video_voice");
  const [agreed, setAgreed] = useState({ apply: false, interview: false, biometric: false });
  const [tried, setTried] = useState(false);
  const values = { company: "Acme Talent", choices: { interview: format } };
  const set = (kind: keyof typeof agreed) => (checked: boolean) =>
    setAgreed((current) => ({ ...current, [kind]: checked }));

  return (
    <Section id="consent" title="Consent (COMP-002)">
      <SegmentedControl
        label="Interview format"
        size="sm"
        value={format}
        onValueChange={setFormat}
        options={[
          { value: "video_voice", label: "Video + voice" },
          { value: "voice_only", label: "Voice only" },
        ]}
      />
      {notices.isPending && <Skeleton className="h-24 max-w-[620px]" />}
      {notices.isError && (
        <p className="text-[15px] text-signal-gap">Couldn&apos;t load the notices from the API.</p>
      )}
      {notices.data && (
        <>
          <Row label={`Apply form · ${notices.data.apply.id}`}>
            <ConsentCheckbox
              className="w-full max-w-[620px]"
              notice={notices.data.apply}
              values={values}
              checked={agreed.apply}
              onCheckedChange={set("apply")}
              error={tried && !agreed.apply ? t("consent.required.apply") : undefined}
            />
          </Row>
          <Row
            label={`Device check · ${notices.data.interview.id}${format === "video_voice" ? ` + ${notices.data.biometric.id}` : ""}`}
          >
            <div className="flex w-full max-w-[640px] flex-col">
              <ConsentCheckbox
                variant="plain"
                notice={notices.data.interview}
                values={values}
                checked={agreed.interview}
                onCheckedChange={set("interview")}
                error={tried && !agreed.interview ? t("consent.required.interview") : undefined}
              />
              {format === "video_voice" && (
                <ConsentCheckbox
                  variant="plain"
                  notice={notices.data.biometric}
                  values={values}
                  checked={agreed.biometric}
                  onCheckedChange={set("biometric")}
                  error={tried && !agreed.biometric ? t("consent.required.interview") : undefined}
                />
              )}
            </div>
          </Row>
          <Row label="Validation">
            <Button variant="secondary" onClick={() => setTried(true)}>
              Try to send
            </Button>
            <Button variant="quiet" onClick={() => setTried(false)}>
              Reset
            </Button>
          </Row>
        </>
      )}
    </Section>
  );
}
