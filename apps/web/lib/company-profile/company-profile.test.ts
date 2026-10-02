import { ApiError } from "@fasthyr/api-client";
import { describe, expect, it } from "vitest";

import {
  type CompanyProfile,
  countryOptions,
  formErrors,
  formFromProfile,
  isWebAddress,
  logoSizeError,
  sameForm,
  saveErrorKey,
  timeZoneOptions,
  updateRequest,
} from "@/lib/company-profile";

const PROFILE: CompanyProfile = {
  company_name: "Acme Talent",
  website: "https://acme.com",
  industry: "technology",
  company_size: null,
  hq_country: "PH",
  timezone: "Asia/Manila",
  about: null,
  careers_url: "http://acme.com/careers",
  logo_url: null,
  banner_url: null,
  updated_at: "2026-10-02T00:00:00Z",
};

describe("company profile form", () => {
  it("shows the website without its https:// prefix and sends blanks as null", () => {
    const form = formFromProfile(PROFILE);
    expect(form.website).toBe("acme.com");
    expect(form.careers_url).toBe("http://acme.com/careers");

    const body = updateRequest(
      { ...form, about: "  ", company_name: " Acme " },
      {},
      {
        logo: true,
        banner: false,
      },
    );
    expect(body).toMatchObject({
      company_name: "Acme",
      website: "acme.com",
      about: null,
      company_size: null,
      remove_logo: true,
      remove_banner: false,
    });
  });

  it("ignores whitespace-only edits when deciding whether anything changed", () => {
    const form = formFromProfile(PROFILE);
    expect(sameForm(form, { ...form, company_name: "Acme Talent " })).toBe(true);
    expect(sameForm(form, { ...form, about: "New" })).toBe(false);
  });

  it("checks the name and web addresses like the API", () => {
    const form = formFromProfile(PROFILE);
    expect(formErrors(form)).toEqual({});
    expect(formErrors({ ...form, company_name: " ", website: "not a url" })).toEqual({
      company_name: "companyProfile.errors.nameRequired",
      website: "companyProfile.errors.website",
    });
    expect(isWebAddress("careers.acme.co.uk/jobs")).toBe(true);
    expect(isWebAddress("https://user:pw@acme.com")).toBe(false);
    expect(isWebAddress("localhost:3000")).toBe(false);
  });

  it("checks the logo is square and big enough", () => {
    expect(logoSizeError(512, 512)).toBeNull();
    expect(logoSizeError(512, 500)).toBe("companyProfile.errors.logoNotSquare");
    expect(logoSizeError(128, 128)).toBe("companyProfile.errors.logoTooSmall");
  });

  it("maps image errors from the API to copy", () => {
    expect(saveErrorKey(new ApiError(422, "logo_not_square", "x"))).toBe(
      "companyProfile.errors.logoNotSquare",
    );
    expect(saveErrorKey(new ApiError(410, "upload_expired", "x"))).toBe(
      "companyProfile.errors.uploadAgain",
    );
    expect(saveErrorKey(new Error("network"))).toBe("companyProfile.errors.saveFailed");
  });
});

describe("select options", () => {
  it("names countries and offsets time zones", () => {
    const countries = countryOptions();
    expect(countries.find((option) => option.value === "PH")?.label).toBe("Philippines");
    expect(countries.length).toBeGreaterThan(240);

    const zones = timeZoneOptions(new Date("2026-01-15T00:00:00Z"));
    expect(zones.find((option) => option.value === "Asia/Manila")?.label).toBe(
      "Asia/Manila (UTC+8)",
    );
    expect(zones.find((option) => option.value === "America/New_York")?.label).toBe(
      "America/New York (UTC−5)",
    );
    expect(zones.some((option) => option.value === "UTC")).toBe(true);
  });
});
