const GITHUB_HOSTS = new Set(["github.com", "www.github.com"]);
const RESERVED_GITHUB_PATHS = new Set([
  "about",
  "apps",
  "blog",
  "business",
  "collections",
  "contact",
  "customer-stories",
  "enterprise",
  "events",
  "explore",
  "features",
  "github",
  "join",
  "login",
  "marketplace",
  "new",
  "notifications",
  "organizations",
  "orgs",
  "pricing",
  "pulls",
  "search",
  "settings",
  "sponsors",
  "topics",
  "trending"
]);

const GITHUB_USERNAME_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/;

export function normalizeGitHubProfileInput(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) {
    return null;
  }

  if (GITHUB_USERNAME_PATTERN.test(trimmed)) {
    return trimmed;
  }

  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;

  try {
    const url = new URL(withScheme);
    if (!GITHUB_HOSTS.has(url.hostname.toLowerCase())) {
      return null;
    }

    const [candidate] = url.pathname.split("/").filter(Boolean);
    if (!candidate || RESERVED_GITHUB_PATHS.has(candidate.toLowerCase())) {
      return null;
    }

    return GITHUB_USERNAME_PATTERN.test(candidate) ? candidate : null;
  } catch {
    return null;
  }
}

