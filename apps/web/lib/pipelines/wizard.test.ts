import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  applyLink,
  applyLinks,
  blockedHint,
  closeDate,
  defaultDepartment,
  defaultReserve,
  departmentOptions,
  emptyForm,
  formFromPipeline,
  joinWithOr,
  NO_DEPARTMENT,
  type Pipeline,
  publishBlock,
  publishErrorKey,
  saveErrorKey,
  setupFromForm,
  startOfDay,
  SHARE_SOURCES,
} from "@/lib/pipelines/wizard";

const filled = {
  ...emptyForm("eng"),
  title: "  Senior Backend Engineer ",
  location: " ",
  jd_text: "Build the payments platform.",
  must_haves: ["Go", "PostgreSQL", "Distributed systems"],
  nice_to_haves: ["Kubernetes"],
  open_to: ["career_changers" as const],
  resume_pass_bar: 70,
  interview_format: "voice_only" as const,
  tone: "direct" as const,
  seniority: "senior" as const,
  skills_to_probe: ["System design", "API design", "Code review"],
  link_expiry_days: 7 as const,
  reminder_enabled: false,
};

describe("blockedHint", () => {
  it("needs 3 must-haves on Role and 3 skills on AI interview", () => {
    const form = { ...filled, must_haves: ["Go", "PostgreSQL"], skills_to_probe: ["A"] };
    expect(blockedHint(form, 0)).toBe("pipelines.wizard.blocked.mustHaves");
    expect(blockedHint(form, 1)).toBe("pipelines.wizard.blocked.skills");
    expect(blockedHint(filled, 0)).toBeNull();
    expect(blockedHint(filled, 1)).toBeNull();
  });
});

describe("scoring, schedule and publishing (PIPE-003)", () => {
  const NOW = new Date(2026, 9, 2, 15, 30);

  it("blocks Scoring until the weights add up to 100", () => {
    expect(blockedHint({ ...filled, weight_technical: 55 }, 2)).toBe(
      "pipelines.wizard.blocked.weights",
    );
    expect(blockedHint(filled, 2)).toBeNull();
  });

  it("starts the reserve at 100, or the free credits in 10s when fewer", () => {
    expect(defaultReserve(null)).toBe(100);
    expect(defaultReserve(788)).toBe(100);
    expect(defaultReserve(47)).toBe(40);
    expect(defaultReserve(0)).toBe(10);
  });

  it("leaves out weights that don't add up yet, so a draft always saves", () => {
    const body = setupFromForm({ ...filled, weight_technical: 55 });
    expect(body).not.toHaveProperty("weight_technical");
    expect(setupFromForm(filled)).toMatchObject({
      weight_technical: 50,
      weight_communication: 30,
      weight_culture: 20,
    });
  });

  it("sends the opening date as local midnight, and nothing when it opens now", () => {
    const later = { ...filled, open_mode: "scheduled" as const, opens_on: "2026-10-05" };
    expect(setupFromForm(later).opens_at).toBe(new Date(2026, 9, 5).toISOString());
    expect(setupFromForm({ ...later, open_mode: "now" }).opens_at).toBeNull();
  });

  it("keeps a scheduled pipeline's open mode and reserve out of its edits", () => {
    const body = setupFromForm(filled, { scheduled: true });
    expect(body).not.toHaveProperty("open_mode");
    expect(body).not.toHaveProperty("credits_to_reserve");
  });

  it("blocks Publish on whatever the API would refuse", () => {
    const ready = { ...filled, location: "Makati", credits_to_reserve: 50 };
    expect(publishBlock(ready, 50, { now: NOW })).toBeNull();
    expect(publishBlock(ready, 40, { now: NOW })).toBe("pipelines.wizard.blocked.credits");
    // Unknown free credits aren't checked here; the API still checks them.
    expect(publishBlock(ready, null, { now: NOW })).toBeNull();
    // A scheduled pipeline already holds its reserve.
    expect(publishBlock(ready, 0, { scheduled: true, now: NOW })).toBeNull();
    expect(publishBlock({ ...ready, title: " " }, 50, { now: NOW })).toBe(
      "pipelines.wizard.blocked.details",
    );
    expect(publishBlock({ ...ready, location: "", work_setup: "remote" }, 50, { now: NOW })).toBe(
      null,
    );
    expect(publishBlock({ ...ready, weight_culture: 25 }, 50, { now: NOW })).toBe(
      "pipelines.wizard.blocked.weights",
    );
    const today = { ...ready, open_mode: "scheduled" as const, opens_on: "2026-10-02" };
    expect(publishBlock(today, 50, { now: NOW })).toBe("pipelines.wizard.blocked.openingDate");
    expect(publishBlock({ ...today, opens_on: "2026-10-03" }, 50, { now: NOW })).toBeNull();
  });

  it("counts the close date from the opening day", () => {
    expect(closeDate({ ...filled, duration_days: 30 }, NOW)).toEqual(new Date(2026, 10, 1));
    const later = { ...filled, open_mode: "scheduled" as const, opens_on: "2026-10-05" };
    expect(closeDate({ ...later, duration_days: 60 }, NOW)).toEqual(new Date(2026, 11, 4));
    expect(startOfDay("2026-10-05")).toEqual(new Date(2026, 9, 5));
  });

  it("explains a failed publish", () => {
    expect(publishErrorKey(new ApiError(409, "insufficient_free_credits", "No"))).toBe(
      "pipelines.wizard.errors.credits",
    );
    expect(publishErrorKey(new Error("offline"))).toBe("pipelines.wizard.errors.publishFailed");
  });

  it("tags the apply link with its source", () => {
    expect(applyLink("https://fasthyr.com", "acme", "support-lead", "linkedin")).toBe(
      "https://fasthyr.com/apply/acme/support-lead?source=linkedin",
    );
  });

  it("builds one tagged link per source for the share tiles", () => {
    const links = applyLinks("https://fasthyr.com", "acme", "support-lead");
    expect(Object.keys(links)).toEqual([...SHARE_SOURCES]);
    expect(links.careers).toBe("https://fasthyr.com/apply/acme/support-lead?source=careers");
  });
});

describe("setupFromForm and formFromPipeline", () => {
  it("sends trimmed text with blanks as null", () => {
    const body = setupFromForm(filled);
    expect(body.title).toBe("Senior Backend Engineer");
    expect(body.location).toBeNull();
    expect(body.department_id).toBe("eng");
  });

  it("restores every field of a saved draft", () => {
    const body = setupFromForm(filled);
    const saved = { ...body, status: "draft" } as unknown as Pipeline;
    expect(formFromPipeline(saved)).toEqual({
      ...filled,
      title: "Senior Backend Engineer",
      location: "",
    });
  });

  it("keeps the defaults for choices a draft never made", () => {
    const saved = {
      ...setupFromForm(emptyForm(null)),
      employment_type: null,
      interview_format: null,
      tone: null,
      seniority: null,
    } as unknown as Pipeline;
    expect(formFromPipeline(saved)).toEqual(emptyForm(null));
  });
});

describe("departmentOptions", () => {
  const departments = [
    { id: "eng", name: "Engineering", assigned: true },
    { id: "ops", name: "Operations", assigned: false },
  ];

  it("gives Admins No department and every department", () => {
    const options = departmentOptions(departments, true, "No department");
    expect(options.map((o) => o.value)).toEqual([NO_DEPARTMENT, "eng", "ops"]);
    expect(defaultDepartment(options, true)).toBeNull();
  });

  it("gives Recruiters only their departments, starting with the first", () => {
    const options = departmentOptions(departments, false, "No department");
    expect(options).toEqual([{ value: "eng", label: "Engineering" }]);
    expect(defaultDepartment(options, false)).toBe("eng");
    expect(defaultDepartment([], false)).toBeNull();
  });
});

describe("helpers", () => {
  it("joins the Also open to list", () => {
    expect(joinWithOr(["a"], "or")).toBe("a");
    expect(joinWithOr(["a", "b"], "or")).toBe("a or b");
    expect(joinWithOr(["a", "b", "c"], "or")).toBe("a, b or c");
  });

  it("explains a failed save", () => {
    expect(saveErrorKey(new ApiError(409, "pipeline_locked", "Locked"))).toBe(
      "pipelines.wizard.errors.locked",
    );
    expect(saveErrorKey(new ApiError(422, "unknown_department", "No"))).toBe(
      "pipelines.wizard.errors.department",
    );
    expect(saveErrorKey(new Error("offline"))).toBe("pipelines.wizard.errors.saveFailed");
  });
});
