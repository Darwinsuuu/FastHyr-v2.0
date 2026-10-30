import { describe, expect, it } from "vitest";

import {
  changeOf,
  type EmailTemplateVersion,
  filterCounts,
  insertable,
  linkHref,
  matchesFilter,
  problems,
  sampleSubject,
  TEMPLATE_KEYS,
  withoutParameterChips,
  withParameterChips,
} from ".";

const BASE = ["Candidate.firstname", "Candidate.lastname", "Job.title", "Company.name"];

describe("parameter chips", () => {
  it("wrap parameters in text and come back as the stored HTML", () => {
    const stored = '<p>Hi [Candidate.firstname], <a href="[Interview.link]">start</a></p>';
    const chips = withParameterChips(stored);
    expect(chips).toBe(
      '<p>Hi <span data-parameter="Candidate.firstname">[Candidate.firstname]</span>, ' +
        '<a href="[Interview.link]">start</a></p>',
    );
    // Tiptap adds its own class to the chip.
    expect(withoutParameterChips(chips.replace("<span ", '<span class="fh-parameter" '))).toBe(
      stored,
    );
  });
});

describe("problems", () => {
  it("mirror the API's checks", () => {
    expect(problems("Hello [Job.title]", "<p>Hi</p>", BASE)).toEqual([]);
    expect(problems("  ", "<p><br></p>", BASE)).toEqual([
      { field: "subject", kind: "missing" },
      { field: "body_html", kind: "missing" },
    ]);
    expect(
      problems("x".repeat(201), "<p>Hi [Interview.link] [Candidate.first_name]</p>", BASE),
    ).toEqual([
      { field: "subject", kind: "too_long" },
      { field: "body_html", kind: "unknown_parameter", parameter: "[Interview.link]" },
      { field: "body_html", kind: "unknown_parameter", parameter: "[Candidate.first_name]" },
    ]);
    // "[sic]" isn't written like a parameter.
    expect(problems("Hi [sic]", "<p>Hi</p>", BASE)).toEqual([]);
  });

  it("never offer the review link, which every rejection gets anyway", () => {
    expect(insertable([...BASE, "Review.link"])).toEqual(BASE);
  });
});

describe("filters", () => {
  it("count every template once, confirmations with the updates", () => {
    expect(filterCounts(TEMPLATE_KEYS)).toEqual({
      all: 10,
      invitations: 1,
      reminders: 2,
      advancement: 1,
      rejections: 2,
      updates: 4,
    });
    expect(matchesFilter("interview_received", "updates")).toBe(true);
    expect(matchesFilter("reject_resume", "updates")).toBe(false);
  });
});

describe("change history", () => {
  const version = (kind: EmailTemplateVersion["kind"], subject: string, body: string) =>
    ({
      id: subject + body,
      kind,
      subject,
      body_html: body,
      created_at: "",
      created_by: null,
    }) as EmailTemplateVersion;

  it("says what each version changed against the one before it", () => {
    const versions = [
      version("restore", "B", "2"),
      version("reset", "A", "1"),
      version("edit", "B", "2"),
      version("edit", "B", "1"),
      version("edit", "A", "1"),
    ];
    expect(versions.map((_, index) => changeOf(versions, index))).toEqual([
      "restored",
      "reset",
      "edited_message",
      "edited_subject",
      "saved",
    ]);
  });
});

describe("links and the test email", () => {
  it("accept web and email addresses only", () => {
    expect(linkHref("acme.test/careers")).toBe("https://acme.test/careers");
    expect(linkHref("https://acme.test")).toBe("https://acme.test");
    expect(linkHref("jobs@acme.test")).toBe("mailto:jobs@acme.test");
    expect(linkHref("javascript:alert(1)")).toBeNull();
    expect(linkHref("not a link")).toBeNull();
  });

  it("fill the subject with the sample candidate", () => {
    expect(
      sampleSubject("[Candidate.firstname], about [Job.title] at [Company.name]", "Acme"),
    ).toBe("Bea, about Senior Backend Engineer at Acme");
  });
});
