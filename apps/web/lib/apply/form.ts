// The application form (APPLY-003, frame Apply, FR-APPLY-03): what the candidate fills in, what
// stops them sending, and what the API's answers mean for them.

import { ApiError, type components } from "@fasthyr/api-client";

import { DIAL_CODES, type PhoneValue } from "@/components/ui/phone-input";
import type { SourceTag } from "@/lib/apply";
import type { MessageKey } from "@/lib/i18n";

export type SubmitApplicationRequest = components["schemas"]["SubmitApplicationRequest"];
export type SubmittedApplication = components["schemas"]["SubmittedApplication"];

export const RESUME_TYPES = ["application/pdf"];
export const RESUME_MAX_BYTES = 10 * 1024 * 1024;

export interface ApplicationForm {
  resume: File | null;
  fullName: string;
  phone: PhoneValue;
  city: string;
  profileUrl: string;
  consent: boolean;
}

export type FormField = "resume" | "fullName" | "phone" | "profileUrl" | "consent";
export type FormErrors = Partial<Record<FormField, MessageKey>>;

/** A new form for this candidate; the name comes from their Google or Microsoft account. */
export function emptyForm(accountName: string, accountEmail: string): ApplicationForm {
  return {
    resume: null,
    // Some accounts have no name, and the session falls back to the email address.
    fullName: accountName === accountEmail ? "" : accountName,
    phone: { country: "PH", number: "" },
    city: "",
    profileUrl: "",
    consent: false,
  };
}

const WEB_LINK = /^https?:\/\/[^\s/$.?#][^\s]*$/i;

export function phoneDigits(number: string): string {
  return number.replace(/\D/g, "");
}

/** What still needs the candidate's attention; empty when the form can be sent. */
export function formErrors(form: ApplicationForm): FormErrors {
  const errors: FormErrors = {};
  if (!form.resume) errors.resume = "apply.form.errors.resume";
  if (!form.fullName.trim()) errors.fullName = "apply.form.errors.fullName";
  const digits = phoneDigits(form.phone.number).length;
  if (digits < 7 || digits > 15) errors.phone = "apply.form.errors.phone";
  const link = form.profileUrl.trim();
  if (link && !WEB_LINK.test(link)) errors.profileUrl = "apply.form.errors.profileUrl";
  if (!form.consent) errors.consent = "apply.form.errors.consent";
  return errors;
}

export function dialCode(country: string): string {
  return DIAL_CODES.find((item) => item.country === country)?.code ?? "+63";
}

/** The request body once the résumé is uploaded. The email is the account's, never sent. */
export function submitRequest(
  form: ApplicationForm,
  {
    pipelineId,
    uploadId,
    noticeId,
    source,
  }: { pipelineId: string; uploadId: string; noticeId: string; source: SourceTag },
): SubmitApplicationRequest {
  const city = form.city.trim();
  const profileUrl = form.profileUrl.trim();
  return {
    pipeline_id: pipelineId,
    upload_id: uploadId,
    resume_filename: form.resume?.name.slice(0, 255) || "resume.pdf",
    full_name: form.fullName.trim(),
    phone_country_code: dialCode(form.phone.country),
    phone: phoneDigits(form.phone.number),
    city: city || null,
    profile_url: profileUrl || null,
    consent_notice_id: noticeId,
    source,
  };
}

/** Why sending failed, and which field it belongs to (null: the footer line). */
export interface SubmitProblem {
  field: FormField | null;
  message: MessageKey;
  /** The role stopped taking applications: nothing the candidate can fix here. */
  closed?: boolean;
}

const PDF_MESSAGES: Record<string, MessageKey> = {
  pdf_not_pdf: "apply.form.errors.pdfNotPdf",
  pdf_too_large: "apply.form.errors.pdfTooLarge",
  pdf_malformed: "apply.form.errors.pdfMalformed",
  pdf_encrypted: "apply.form.errors.pdfEncrypted",
  pdf_too_many_pages: "apply.form.errors.pdfTooManyPages",
};

export function submitProblem(error: unknown): SubmitProblem {
  const code = error instanceof ApiError ? error.code : undefined;
  if (code && code in PDF_MESSAGES) return { field: "resume", message: PDF_MESSAGES[code]! };
  if (code === "upload_missing" || code === "upload_expired") {
    return { field: "resume", message: "apply.form.errors.uploadAgain" };
  }
  if (code === "pipeline_not_accepting" || (error instanceof ApiError && error.status === 404)) {
    return { field: null, message: "apply.form.errors.notAccepting", closed: true };
  }
  if (code === "notice_outdated" || code === "notice_unknown") {
    return { field: null, message: "apply.form.errors.noticeChanged" };
  }
  if (code === "candidate_sign_in_required" || code === "unauthenticated") {
    return { field: null, message: "apply.form.errors.signIn" };
  }
  return { field: null, message: "apply.form.errors.failed" };
}

/** "Thanks, Paolo." */
export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? "";
}
