import { redirect } from "next/navigation";
import { normalizeGitHubProfileInput } from "@/lib/github-profile";

export function GET(request: Request): never {
  const url = new URL(request.url);
  const username = normalizeGitHubProfileInput(url.searchParams.get("username") ?? "");
  redirect(username ? `/${encodeURIComponent(username)}` : "/?error=invalid-profile#profile-search");
}
