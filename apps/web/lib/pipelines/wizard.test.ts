import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  blockedHint,
  defaultDepartment,
  departmentOptions,
  emptyForm,
  formFromPipeline,
  joinWithOr,
  NO_DEPARTMENT,
  type Pipeline,
  saveErrorKey,
  setupFromForm,
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
