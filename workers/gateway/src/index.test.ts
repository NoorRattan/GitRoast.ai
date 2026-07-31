import { describe, expect, it, vi } from "vitest";

import { handleGatewayRequest } from "./index";

const env = {
  ORIGIN_BASE_URL: "https://origin.example",
  ALLOWED_ORIGIN: "https://frontend.example",
  GATEWAY_SHARED_SECRET: "gateway-secret"
};

describe("API gateway", () => {
  it("strips caller-controlled forwarding headers and injects its own identity", async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("cf-connecting-ip")).toBeNull();
      expect(headers.get("x-forwarded-for")).toBeNull();
      expect(headers.get("x-gitroast-client-ip")).toBe("203.0.113.9");
      expect(headers.get("x-gitroast-gateway-secret")).toBe("gateway-secret");
      return new Response('{"status":"ok"}', { headers: { "content-type": "application/json" } });
    });
    const response = await handleGatewayRequest(
      new Request("https://gateway.example/api/v1/audit", {
        method: "POST",
        headers: {
          origin: env.ALLOWED_ORIGIN,
          "cf-connecting-ip": "203.0.113.9",
          "x-forwarded-for": "198.51.100.3",
          "x-gitroast-client-ip": "198.51.100.4",
          "content-type": "application/json"
        },
        body: "{}"
      }),
      env,
      fetcher
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("access-control-allow-origin")).toBe(env.ALLOWED_ORIGIN);
    expect(fetcher).toHaveBeenCalledWith(expect.objectContaining({ href: "https://origin.example/api/v1/audit" }), expect.any(Object));
  });

  it("rejects direct browser origins and missing Cloudflare identities", async () => {
    const untrusted = await handleGatewayRequest(new Request("https://gateway.example/api/v1/audit", {
      headers: { origin: "https://attacker.example", "cf-connecting-ip": "203.0.113.9" }
    }), env);
    const missingIdentity = await handleGatewayRequest(new Request("https://gateway.example/api/v1/audit"), env);

    expect(untrusted.status).toBe(403);
    expect(missingIdentity.status).toBe(400);
  });

  it("responds to an allowed CORS preflight without touching Render", async () => {
    const response = await handleGatewayRequest(new Request("https://gateway.example/api/v1/audit", {
      method: "OPTIONS",
      headers: { origin: env.ALLOWED_ORIGIN }
    }), env);

    expect(response.status).toBe(204);
    expect(response.headers.get("access-control-allow-methods")).toContain("POST");
  });
});
