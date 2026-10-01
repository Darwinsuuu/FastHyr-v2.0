// The signed-in TA user as server pages read it from the Supabase session claims.

export interface ClaimsUser {
  id: string;
  email: string;
  fullName: string;
  avatarUrl: string | null;
}

export type SessionClaims = {
  sub: string;
  email?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
    avatar_url?: string;
    picture?: string;
    email_verified?: boolean;
  };
};

/** False only for email + password accounts that haven't verified yet (FR-AUTH-03). */
export function isVerified(claims: SessionClaims): boolean {
  return claims.user_metadata?.email_verified !== false;
}

export function userFromClaims(claims: SessionClaims): ClaimsUser {
  const metadata = claims.user_metadata ?? {};
  return {
    id: claims.sub,
    email: claims.email ?? "",
    fullName: metadata.full_name || metadata.name || "",
    avatarUrl: metadata.avatar_url || metadata.picture || null,
  };
}
