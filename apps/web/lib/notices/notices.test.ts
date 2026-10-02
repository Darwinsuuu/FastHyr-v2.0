import { describe, expect, it } from "vitest";

import { fillNotice, type Notice, noticeLinkHref } from "@/lib/notices";

const apply: Notice = {
  id: "apply@v1",
  kind: "apply",
  version: 1,
  statement: "I agree that {company} can review my application and invite me to {interview}.",
  details: ["A person on the {company} team decides."],
  links: ["privacy"],
  choices: {
    interview: {
      video_voice: "an AI interview by video and voice",
      voice_only: "an AI interview by voice",
    },
  },
};

describe("fillNotice", () => {
  it("fills the company and the pipeline's interview format", () => {
    const filled = fillNotice(apply, {
      company: "Acme Talent",
      choices: { interview: "voice_only" },
    });
    expect(filled).toEqual({
      id: "apply@v1",
      statement:
        "I agree that Acme Talent can review my application and invite me to an AI interview by voice.",
      details: ["A person on the Acme Talent team decides."],
      links: ["privacy"],
    });
  });

  it("refuses to show a consent with a gap in it", () => {
    expect(() => fillNotice(apply, { company: "Acme Talent" })).toThrow("{interview}");
    expect(() =>
      fillNotice(apply, { company: "Acme Talent", choices: { interview: "hologram" } }),
    ).toThrow("{interview}");
  });
});

describe("noticeLinkHref", () => {
  it("points at the public site", () => {
    expect(noticeLinkHref("ai_in_hiring")).toMatch(/\/ai-in-hiring$/);
  });
});
