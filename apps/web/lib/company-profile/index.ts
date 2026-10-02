// Company profile page logic (WS-001): the form, its rules, the select options and save errors.

import { ApiError, type components } from "@fasthyr/api-client";

import type { MessageKey } from "@/lib/i18n";

export type CompanyProfile = components["schemas"]["CompanyProfile"];
export type UpdateCompanyProfile = components["schemas"]["UpdateCompanyProfileRequest"];
export type BrandingKind = components["schemas"]["BrandingKind"];

/** Same limits as the API. */
export const COMPANY_NAME_MAX = 120;
export const ABOUT_MAX = 600;
export const URL_MAX = 300;

export const IMAGE_MAX_BYTES = 2 * 1024 * 1024;
export const LOGO_MIN_SIDE = 256;
/** SVG logos are drawn to a PNG this size in the browser; the API never takes SVG. */
export const LOGO_RASTER_SIDE = 512;
export const LOGO_TYPES = ["image/png", "image/svg+xml"];
export const BANNER_TYPES = ["image/png", "image/jpeg"];

export const INDUSTRIES = [
  "technology",
  "finance",
  "healthcare",
  "bpo",
  "retail",
  "manufacturing",
  "government",
  "other",
] as const;
export const COMPANY_SIZES = ["1-50", "51-200", "201-1000", "1001-5000", "5000+"] as const;

// ISO 3166-1 alpha-2 codes (plus Kosovo, XK); names come from Intl.DisplayNames.
const COUNTRY_CODES = (
  "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS " +
  "BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE " +
  "EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM " +
  "HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC " +
  "LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA " +
  "NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW " +
  "SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO " +
  "TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW"
).split(" ");

export interface Option {
  value: string;
  label: string;
}

export function countryOptions(locale = "en"): Option[] {
  const names = new Intl.DisplayNames([locale], { type: "region" });
  return COUNTRY_CODES.map((code) => ({ value: code, label: names.of(code) ?? code })).sort(
    (a, b) => a.label.localeCompare(b.label, locale),
  );
}

/** "+8", "-3:30" or "" (UTC) for `timeZone` at `at`. */
export function utcOffset(timeZone: string, at: Date): string {
  const part = new Intl.DateTimeFormat("en-US", { timeZone, timeZoneName: "shortOffset" })
    .formatToParts(at)
    .find((item) => item.type === "timeZoneName");
  return (part?.value ?? "GMT").replace("GMT", "");
}

/** Every IANA time zone as "Asia/Manila (UTC+8)", by offset then name. */
export function timeZoneOptions(at: Date = new Date()): Option[] {
  const zones = Intl.supportedValuesOf("timeZone");
  if (!zones.includes("UTC")) zones.push("UTC");
  const minutes = (offset: string) => {
    const match = /^([+-])(\d+)(?::(\d+))?$/.exec(offset.replace("−", "-"));
    if (!match) return 0;
    const value = Number(match[2]) * 60 + Number(match[3] ?? 0);
    return match[1] === "-" ? -value : value;
  };
  return zones
    .map((zone) => ({ zone, offset: utcOffset(zone, at) }))
    .sort((a, b) => minutes(a.offset) - minutes(b.offset) || a.zone.localeCompare(b.zone))
    .map(({ zone, offset }) => ({
      value: zone,
      label: `${zone.replaceAll("_", " ")} (UTC${offset.replace("-", "−")})`,
    }));
}

/** What the inputs hold. The website input sits after an "https://" prefix. */
export interface ProfileForm {
  company_name: string;
  website: string;
  industry: string;
  company_size: string;
  hq_country: string;
  timezone: string;
  about: string;
  careers_url: string;
}

export function formFromProfile(profile: CompanyProfile): ProfileForm {
  return {
    company_name: profile.company_name,
    website: (profile.website ?? "").replace(/^https:\/\//i, ""),
    industry: profile.industry ?? "",
    company_size: profile.company_size ?? "",
    hq_country: profile.hq_country ?? "",
    timezone: profile.timezone ?? "",
    about: profile.about ?? "",
    careers_url: profile.careers_url ?? "",
  };
}

/** A new image waiting to upload, or the current one marked for removal. */
export type ImageChange = { file: File; previewUrl: string } | "remove" | null;

export function sameForm(a: ProfileForm, b: ProfileForm): boolean {
  return (Object.keys(a) as (keyof ProfileForm)[]).every((key) => a[key].trim() === b[key].trim());
}

const HOST = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/i;

/** A rough check matching the API's: http(s), a dotted host, no user or port. */
export function isWebAddress(value: string): boolean {
  const trimmed = value.trim();
  const url = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
  try {
    const parsed = new URL(url);
    return HOST.test(parsed.hostname) && !parsed.username && !parsed.password && parsed.port === "";
  } catch {
    return false;
  }
}

export type FormErrors = Partial<Record<keyof ProfileForm, MessageKey>>;

export function formErrors(form: ProfileForm): FormErrors {
  const errors: FormErrors = {};
  if (!form.company_name.trim()) errors.company_name = "companyProfile.errors.nameRequired";
  if (form.website.trim() && !isWebAddress(form.website))
    errors.website = "companyProfile.errors.website";
  if (form.careers_url.trim() && !isWebAddress(form.careers_url))
    errors.careers_url = "companyProfile.errors.website";
  return errors;
}

export function updateRequest(
  form: ProfileForm,
  uploads: { logo_upload_id?: string; banner_upload_id?: string },
  remove: { logo: boolean; banner: boolean },
): UpdateCompanyProfile {
  const optional = (value: string) => value.trim() || null;
  return {
    company_name: form.company_name.trim(),
    website: optional(form.website),
    industry: (optional(form.industry) as UpdateCompanyProfile["industry"]) ?? null,
    company_size: (optional(form.company_size) as UpdateCompanyProfile["company_size"]) ?? null,
    hq_country: optional(form.hq_country),
    timezone: optional(form.timezone),
    about: optional(form.about),
    careers_url: optional(form.careers_url),
    remove_logo: remove.logo,
    remove_banner: remove.banner,
    ...uploads,
  };
}

const SAVE_ERRORS: Record<string, MessageKey> = {
  image_invalid: "companyProfile.errors.imageInvalid",
  image_too_large: "companyProfile.errors.imageTooLarge",
  image_too_big: "companyProfile.errors.imageTooBig",
  logo_not_square: "companyProfile.errors.logoNotSquare",
  logo_too_small: "companyProfile.errors.logoTooSmall",
  upload_missing: "companyProfile.errors.uploadAgain",
  upload_expired: "companyProfile.errors.uploadAgain",
};

export function saveErrorKey(error: unknown): MessageKey {
  if (error instanceof ApiError && error.code in SAVE_ERRORS) {
    return SAVE_ERRORS[error.code] as MessageKey;
  }
  return "companyProfile.errors.saveFailed";
}

/** Checks a picked logo before upload: its pixel size, read in the browser. */
export function logoSizeError(width: number, height: number): MessageKey | null {
  if (width !== height) return "companyProfile.errors.logoNotSquare";
  if (width < LOGO_MIN_SIDE) return "companyProfile.errors.logoTooSmall";
  return null;
}
