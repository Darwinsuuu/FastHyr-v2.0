import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  type ApplicationForm,
  checkResume,
  emptyForm,
  firstName,
  formErrors,
  submitProblem,
  RESUME_MAX_BYTES,
  submitRequest,
  uploadResume,
} from "@/lib/apply/form";

const resume = new File(["%PDF-1.7"], "paolo-reyes-resume.pdf", { type: "application/pdf" });

function filled(changes: Partial<ApplicationForm> = {}): ApplicationForm {
  return {
    ...emptyForm("Paolo Reyes", "paolo@example.com"),
    resume,
    phone: { country: "PH", number: "917 123 4567" },
    consent: true,
    ...changes,
  };
}

describe("application form", () => {
  it("prefills the account name, but not an email standing in for one", () => {
    expect(emptyForm("Paolo Reyes", "paolo@example.com").fullName).toBe("Paolo Reyes");
    expect(emptyForm("paolo@example.com", "paolo@example.com").fullName).toBe("");
  });

  it("needs a résumé, a name, a reachable number and consent", () => {
    expect(formErrors(filled())).toEqual({});
    expect(Object.keys(formErrors(emptyForm("", "a@example.com"))).sort()).toEqual([
      "consent",
      "fullName",
      "phone",
      "resume",
    ]);
    expect(formErrors(filled({ phone: { country: "PH", number: "917 12" } })).phone).toBeDefined();
    expect(formErrors(filled({ fullName: "   " })).fullName).toBeDefined();
  });

  it("accepts only web links for LinkedIn or portfolio, and none at all", () => {
    expect(formErrors(filled({ profileUrl: "" })).profileUrl).toBeUndefined();
    expect(formErrors(filled({ profileUrl: "https://linkedin.com/in/x" })).profileUrl).toBe(
      undefined,
    );
    expect(formErrors(filled({ profileUrl: "linkedin.com/in/x" })).profileUrl).toBeDefined();
    expect(formErrors(filled({ profileUrl: "javascript:alert(1)" })).profileUrl).toBeDefined();
  });

  it("sends digits with the dialling code, blanks as null and the notice it showed", () => {
    const body = submitRequest(
      filled({ city: "  ", phone: { country: "SG", number: "8123 4567" } }),
      {
        pipelineId: "p1",
        uploadId: "u1",
        noticeId: "apply@v1",
        source: "linkedin",
      },
    );
    expect(body).toMatchObject({
      pipeline_id: "p1",
      upload_id: "u1",
      resume_filename: "paolo-reyes-resume.pdf",
      full_name: "Paolo Reyes",
      phone_country_code: "+65",
      phone: "81234567",
      city: null,
      profile_url: null,
      consent_notice_id: "apply@v1",
      source: "linkedin",
    });
    expect(body).not.toHaveProperty("email");
  });

  it("explains what the API refused, next to the field it belongs to", () => {
    const refused = (status: number, code: string) => new ApiError(status, code, "");
    expect(submitProblem(refused(422, "pdf_encrypted"))).toEqual({
      field: "resume",
      message: "apply.form.errors.pdfEncrypted",
    });
    expect(submitProblem(refused(409, "pipeline_not_accepting"))).toMatchObject({
      field: null,
      closed: true,
    });
    expect(submitProblem(refused(409, "notice_outdated")).message).toBe(
      "apply.form.errors.noticeChanged",
    );
    expect(submitProblem(refused(500, "internal_error")).message).toBe("apply.form.errors.failed");
    // No answer at all: the connection, not the application.
    expect(submitProblem(new TypeError("Failed to fetch")).message).toBe(
      "apply.form.errors.network",
    );
  });

  it("checks the résumé before anything is sent", async () => {
    const pdf = (name: string, type: string, body = "%PDF-1.7 ...") =>
      new File([body], name, { type });
    expect(await checkResume(pdf("cv.pdf", "application/pdf"))).toBeNull();
    // Some phones and Windows give PDFs no type; the name and the first bytes decide.
    expect(await checkResume(pdf("cv.pdf", ""))).toBeNull();
    expect(await checkResume(pdf("cv.pdf", "application/octet-stream"))).toBeNull();
    expect(await checkResume(pdf("cv.docx", ""))).toBe("apply.form.errors.pdfNotPdf");
    expect(await checkResume(pdf("cv.pdf", "application/pdf", "PK\u0003\u0004 word"))).toBe(
      "apply.form.errors.pdfNotPdf",
    );
    expect(await checkResume(pdf("cv.pdf", "application/pdf", ""))).toBe(
      "apply.form.errors.pdfEmpty",
    );
    const large = new File([new Uint8Array(RESUME_MAX_BYTES + 1)], "cv.pdf", {
      type: "application/pdf",
    });
    expect(await checkResume(large)).toBe("apply.form.errors.pdfTooLarge");
  });

  it("retries a dropped upload once, then gives up", async () => {
    const answers = (...steps: (number | "offline")[]) => {
      const calls: number[] = [];
      const send = (async () => {
        const step = steps[calls.length] ?? 200;
        calls.push(1);
        if (step === "offline") throw new TypeError("Failed to fetch");
        return new Response(null, { status: step });
      }) as typeof fetch;
      return { send, calls };
    };
    const once = answers("offline", 200);
    expect(await uploadResume("https://storage", resume, once.send)).toBe("uploaded");
    expect(once.calls).toHaveLength(2);
    const down = answers(503, 503, 200);
    expect(await uploadResume("https://storage", resume, down.send)).toBe("failed");
    expect(down.calls).toHaveLength(2);
    // A refusal won't change on a retry.
    const large = answers(413);
    expect(await uploadResume("https://storage", resume, large.send)).toBe("too_large");
    expect(large.calls).toHaveLength(1);
  });

  it("thanks the candidate by first name", () => {
    expect(firstName("  Paolo  Reyes ")).toBe("Paolo");
    expect(firstName("")).toBe("");
  });
});
