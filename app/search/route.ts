import { redirect } from "next/navigation";

export function GET(request: Request): never {
  const url = new URL(request.url);
  const username = url.searchParams.get("username")?.trim();
  redirect(username ? `/${encodeURIComponent(username)}` : "/");
}
