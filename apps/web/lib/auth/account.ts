// What the user profile modal shows (FR-AUTH-08), from the Supabase Auth user. The web reads
// it straight from Auth, which AGENTS.md hard rule 3 allows; nothing here touches tables.

/** The subset of the Supabase Auth `User` this module reads. */
export interface AuthUserLike {
  id: string;
  email?: string | null;
  email_confirmed_at?: string | null;
  created_at: string;
  last_sign_in_at?: string | null;
  app_metadata?: { provider?: string; providers?: string[] } | null;
  user_metadata?: {
    full_name?: string;
    name?: string;
    avatar_url?: string;
    picture?: string;
  } | null;
  identities?: { provider: string }[] | null;
}

export type SignInMethod = "google" | "microsoft" | "email";

/** Google and Microsoft first (the buttons' order on /login), then email + password. */
const METHOD_ORDER: SignInMethod[] = ["google", "microsoft", "email"];

const PROVIDER_TO_METHOD: Record<string, SignInMethod> = {
  google: "google",
  azure: "microsoft",
  email: "email",
};

export interface AccountDetails {
  id: string;
  name: string;
  avatarUrl: string | null;
  email: string;
  emailVerified: boolean;
  methods: SignInMethod[];
  lastSignInAt: string | null;
  createdAt: string;
  /** The provider the name and photo come from, or null for email + password only. */
  profileSource: Exclude<SignInMethod, "email"> | null;
}

const isIdentityProvider = (method: SignInMethod): method is "google" | "microsoft" =>
  method !== "email";

/** Every way this account can sign in, in a fixed order, without duplicates. */
export function signInMethods(user: AuthUserLike): SignInMethod[] {
  const providers = [
    ...(user.identities ?? []).map((identity) => identity.provider),
    ...(user.app_metadata?.providers ?? []),
    ...(user.app_metadata?.provider ? [user.app_metadata.provider] : []),
  ];
  const found = new Set(providers.map((provider) => PROVIDER_TO_METHOD[provider]));
  return METHOD_ORDER.filter((method) => found.has(method));
}

export function accountDetails(user: AuthUserLike): AccountDetails {
  const email = user.email ?? "";
  const meta = user.user_metadata ?? {};
  const methods = signInMethods(user);
  return {
    id: user.id,
    name: meta.full_name || meta.name || email,
    avatarUrl: meta.avatar_url || meta.picture || null,
    email,
    emailVerified: Boolean(user.email_confirmed_at),
    methods,
    lastSignInAt: user.last_sign_in_at ?? null,
    createdAt: user.created_at,
    profileSource: methods.find(isIdentityProvider) ?? null,
  };
}
