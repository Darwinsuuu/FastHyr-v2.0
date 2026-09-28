# ADR-014: Candidates sign in with Google or Microsoft only

- **Status:** Accepted
- **Date:** 2026-09-29

## Decision
- Candidates must sign in with **Google or Microsoft** (Supabase OAuth) before applying. No email/password and no magic link for candidates in MVP.
- The interview link also requires the candidate to be signed in with the **same account** that applied, which strengthens identity for integrity checks.

## Consequences
- Some candidates without these accounts cannot apply. The apply page says so and points to the employer's contact (company website) as the alternative route. Monitor drop-off at the sign-in step; revisit post-MVP (email magic link).
- Only name, email and avatar are requested from the providers (minimal scopes).
