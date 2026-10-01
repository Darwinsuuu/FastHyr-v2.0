// Scrub rules for Sentry events from the web (FND-009, SECURITY.md §3, NFR-03). The same rules
// as the API's app/core/scrub.py: values under personal or secret keys are replaced, emails and
// tokens inside any other text are masked, URLs lose their query string and fragment, and invite
// tokens in /join/… paths are replaced. Inputs are copied, never changed in place.

export const FILTERED = "[Filtered]";
export const EMAIL_MASK = "[email]";

const SENSITIVE_KEYS = new Set([
  "email",
  "emails",
  "name",
  "names",
  "full_name",
  "first_name",
  "last_name",
  "display_name",
  "phone",
  "address",
  "password",
  "secret",
  "token",
  "access_token",
  "refresh_token",
  "token_hash",
  "code",
  "authorization",
  "cookie",
  "cookies",
  "set_cookie",
  "api_key",
  "apikey",
  "dsn",
  "resume",
  "resume_text",
  "transcript",
  "query_string",
]);
const SAFE_KEYS = new Set(["error_code", "status_code", "api_code", "filename", "function_name"]);
// Request headers worth keeping; everything else (Authorization, Cookie, …) is dropped.
const SAFE_HEADERS = new Set(["content-type", "user-agent", "x-request-id", "x-workspace-id"]);

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+/g;
const BEARER = /\bbearer\s+[A-Za-z0-9._~+/=-]+/gi;
const JWT = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
// Paths whose segments are secrets: the invite link token or code (AUTH-004).
const SECRET_PATH = /(\/join\/)[^/?#\s]+/g;
const MAX_DEPTH = 12;

type Json = Record<string, unknown>;

export function isSensitiveKey(key: string): boolean {
  const normal = key.toLowerCase().replaceAll("-", "_");
  if (SAFE_KEYS.has(normal)) return false;
  if (SENSITIVE_KEYS.has(normal)) return true;
  for (const sensitive of SENSITIVE_KEYS) {
    if (normal.endsWith(`_${sensitive}`)) return true;
  }
  return false;
}

export function scrubText(text: string): string {
  return text
    .replace(BEARER, `Bearer ${FILTERED}`)
    .replace(JWT, FILTERED)
    .replace(EMAIL, EMAIL_MASK)
    .replace(SECRET_PATH, `$1${FILTERED}`);
}

/** The URL without its query string or fragment, with secret path segments replaced. */
export function scrubUrl(url: string): string {
  const cut = url.search(/[?#]/);
  return scrubText(cut === -1 ? url : url.slice(0, cut));
}

export function scrub<T>(value: T, depth = 0): T {
  if (depth > MAX_DEPTH) return FILTERED as T;
  if (typeof value === "string") return scrubText(value) as T;
  if (Array.isArray(value)) return value.map((item) => scrub(item, depth + 1)) as T;
  if (value && typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    const out: Json = {};
    for (const [key, item] of Object.entries(value as Json)) {
      out[key] = isSensitiveKey(key) && item != null ? FILTERED : scrub(item, depth + 1);
    }
    return out as T;
  }
  return value;
}

type Breadcrumb = { message?: string; data?: Json; [key: string]: unknown };

export function scrubBreadcrumb<B extends object>(crumb: B): B {
  const out: Breadcrumb = { ...(crumb as Breadcrumb) };
  if (typeof out.message === "string") out.message = scrubText(out.message);
  if (out.data && typeof out.data === "object") {
    const data = scrub(out.data);
    for (const key of ["url", "from", "to"]) {
      if (typeof data[key] === "string") data[key] = scrubUrl(data[key] as string);
    }
    out.data = data;
  }
  return out as B;
}

// Sentry's SDK contexts describe the browser, OS and trace, not people.
const SDK_CONTEXTS = new Set(["trace", "runtime", "os", "device", "app", "browser", "culture"]);

type SentryLikeEvent = {
  message?: string;
  transaction?: string;
  request?: {
    url?: string;
    method?: string;
    headers?: Record<string, string>;
    [key: string]: unknown;
  };
  user?: { id?: string | number; [key: string]: unknown };
  extra?: Json;
  tags?: Json;
  contexts?: Record<string, unknown>;
  exception?: { values?: { value?: string; stacktrace?: unknown; [key: string]: unknown }[] };
  breadcrumbs?: Breadcrumb[];
  server_name?: string;
  [key: string]: unknown;
};

type Frame = {
  vars?: unknown;
  pre_context?: string[];
  context_line?: string;
  post_context?: string[];
};

// Frames lose local variables, and their source lines are masked like any other text.
function scrubStacktrace(stacktrace: unknown): unknown {
  const frames = (stacktrace as { frames?: Frame[] } | undefined)?.frames;
  if (!frames) return stacktrace;
  return {
    ...(stacktrace as object),
    frames: frames.map((frame) => {
      const { vars, ...rest } = frame;
      void vars;
      return scrub(rest);
    }),
  };
}

/** `beforeSend`: removes anything that could be personal data from an event. */
export function scrubEvent<E extends object>(event: E): E {
  const out: SentryLikeEvent = { ...(event as SentryLikeEvent) };
  if (out.request) {
    const headers = Object.fromEntries(
      Object.entries(out.request.headers ?? {}).filter(([key]) =>
        SAFE_HEADERS.has(key.toLowerCase()),
      ),
    );
    out.request = {
      method: out.request.method,
      url: out.request.url ? scrubUrl(out.request.url) : undefined,
      headers,
    };
  }
  if (out.user) out.user = out.user.id != null ? { id: out.user.id } : {};
  if (typeof out.message === "string") out.message = scrubText(out.message);
  if (typeof out.transaction === "string") out.transaction = scrubUrl(out.transaction);
  if (out.extra) out.extra = scrub(out.extra);
  if (out.tags) out.tags = scrub(out.tags);
  if (out.contexts) {
    out.contexts = Object.fromEntries(
      Object.entries(out.contexts).map(([name, value]) => [
        name,
        SDK_CONTEXTS.has(name) ? value : scrub(value),
      ]),
    );
  }
  if (out.exception?.values) {
    out.exception = {
      ...out.exception,
      values: out.exception.values.map((exception) => ({
        ...exception,
        value: typeof exception.value === "string" ? scrubText(exception.value) : exception.value,
        stacktrace: scrubStacktrace(exception.stacktrace),
      })),
    };
  }
  if (out.breadcrumbs) out.breadcrumbs = out.breadcrumbs.map(scrubBreadcrumb);
  delete out.server_name;
  return out as E;
}
