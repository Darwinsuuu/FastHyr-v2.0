import messages from "@/messages/en.json";

// UI copy lives in messages/en.json (NFR-12). Keys are dotted paths: t("auth.signIn").
// Placeholders in braces are filled from `vars`; counted phrases use plural().

type PluralForms = { one: string; other: string };

type Leaves<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends string
    ? `${Prefix}${K}`
    : T[K] extends PluralForms
      ? never
      : Leaves<T[K], `${Prefix}${K}.`>;
}[keyof T & string];

type PluralLeaves<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends PluralForms
    ? `${Prefix}${K}`
    : T[K] extends string
      ? never
      : PluralLeaves<T[K], `${Prefix}${K}.`>;
}[keyof T & string];

export type MessageKey = Leaves<typeof messages>;
export type PluralKey = PluralLeaves<typeof messages>;

const pluralRules = new Intl.PluralRules("en");

function lookup(key: string): unknown {
  return key
    .split(".")
    .reduce<unknown>(
      (node, part) => (node as Record<string, unknown> | undefined)?.[part],
      messages,
    );
}

function fill(value: string, vars?: Record<string, string | number>): string {
  return vars
    ? value.replace(/\{(\w+)\}/g, (match, name: string) =>
        name in vars ? String(vars[name]) : match,
      )
    : value;
}

export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  const value = lookup(key);
  if (typeof value !== "string") {
    throw new Error(`Missing message: ${key}`);
  }
  return fill(value, vars);
}

/** Picks the "one" or "other" form by `count`: plural("app.memberCount", 3) → "3 members". */
export function plural(
  key: PluralKey,
  count: number,
  vars?: Record<string, string | number>,
): string {
  const forms = lookup(key) as PluralForms;
  const form = pluralRules.select(count) === "one" ? forms.one : forms.other;
  return fill(form, { count, ...vars });
}
