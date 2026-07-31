export type GatewayEnv = {
  ORIGIN_BASE_URL: string;
  ALLOWED_ORIGIN: string;
  GATEWAY_SHARED_SECRET: string;
};

const FORWARDED_HEADERS = [
  "cf-connecting-ip",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-proto",
  "x-real-ip",
  "x-gitroast-client-ip",
  "x-gitroast-gateway-secret"
];

const CORS_HEADERS = "authorization, content-type";
const CORS_METHODS = "GET, POST, DELETE, OPTIONS";

const worker = {
  async fetch(request: Request, env: GatewayEnv): Promise<Response> {
    return handleGatewayRequest(request, env);
  }
};

export default worker;

export async function handleGatewayRequest(request: Request, env: GatewayEnv, fetcher: typeof fetch = fetch): Promise<Response> {
  const incomingUrl = new URL(request.url);
  const origin = request.headers.get("origin");
  if (request.method === "OPTIONS") {
    return preflightResponse(origin, env.ALLOWED_ORIGIN);
  }
  if (!incomingUrl.pathname.startsWith("/api/v1/")) {
    return errorResponse(404, "not_found", "API route not found.", origin, env.ALLOWED_ORIGIN);
  }
  if (origin !== null && origin !== env.ALLOWED_ORIGIN) {
    return errorResponse(403, "origin_forbidden", "This origin is not allowed.", origin, env.ALLOWED_ORIGIN);
  }

  const clientIp = request.headers.get("cf-connecting-ip");
  if (!isIpAddress(clientIp)) {
    return errorResponse(400, "invalid_client_identity", "Cloudflare did not provide a valid client identity.", origin, env.ALLOWED_ORIGIN);
  }

  const upstreamUrl = new URL(incomingUrl.pathname + incomingUrl.search, env.ORIGIN_BASE_URL);
  const headers = new Headers(request.headers);
  for (const header of FORWARDED_HEADERS) {
    headers.delete(header);
  }
  headers.set("x-gitroast-client-ip", clientIp);
  headers.set("x-gitroast-gateway-secret", env.GATEWAY_SHARED_SECRET);

  const upstream = await fetcher(upstreamUrl, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    redirect: "manual"
  });
  return withCors(upstream, origin, env.ALLOWED_ORIGIN);
}

function preflightResponse(origin: string | null, allowedOrigin: string): Response {
  if (origin !== allowedOrigin) {
    return errorResponse(403, "origin_forbidden", "This origin is not allowed.", origin, allowedOrigin);
  }
  return new Response(null, {
    status: 204,
    headers: corsHeaders(origin, allowedOrigin)
  });
}

function withCors(response: Response, origin: string | null, allowedOrigin: string): Response {
  const headers = new Headers(response.headers);
  for (const header of ["access-control-allow-origin", "access-control-allow-credentials", "access-control-allow-headers", "access-control-allow-methods", "vary"]) {
    headers.delete(header);
  }
  for (const [key, value] of corsHeaders(origin, allowedOrigin)) {
    headers.set(key, value);
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function corsHeaders(origin: string | null, allowedOrigin: string): Headers {
  const headers = new Headers({ vary: "Origin" });
  if (origin === allowedOrigin) {
    headers.set("access-control-allow-origin", allowedOrigin);
    headers.set("access-control-allow-credentials", "true");
    headers.set("access-control-allow-headers", CORS_HEADERS);
    headers.set("access-control-allow-methods", CORS_METHODS);
  }
  return headers;
}

function errorResponse(status: number, code: string, message: string, origin: string | null, allowedOrigin: string): Response {
  return new Response(JSON.stringify({ error: { code, message } }), {
    status,
    headers: { "content-type": "application/json", ...Object.fromEntries(corsHeaders(origin, allowedOrigin)) }
  });
}

function isIpAddress(value: string | null): value is string {
  if (value === null || value.length > 45) {
    return false;
  }
  const ipv4 = /^(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}$/.test(value);
  const ipv6 = /^[0-9a-fA-F:]+$/.test(value) && value.includes(":");
  return ipv4 || ipv6;
}
