// ---------------------------------------------------------------------------
// Shared runtime config — single source for both api.ts and auth.ts so
// neither has to import the other (avoids a circular dependency).
// ---------------------------------------------------------------------------

const rawUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/+$/, "");

// Automatically ensure /api/v1 suffix so endpoints like /auth/login and /projects
// match the FastAPI backend routes regardless of how the env var was entered.
export const API_BASE_URL = rawUrl
  ? rawUrl.endsWith("/api/v1")
    ? rawUrl
    : `${rawUrl}/api/v1`
  : "";

export const USE_BACKEND = process.env.NEXT_PUBLIC_USE_BACKEND === "true" || !!rawUrl;
