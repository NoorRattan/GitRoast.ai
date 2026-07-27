const BACKEND_API_BASE_URL = "https://gitroast-ai.onrender.com/api/v1";

type ProxyRouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

export async function GET(request: Request, context: ProxyRouteContext): Promise<Response> {
  return proxyToBackend(request, context);
}

export async function POST(request: Request, context: ProxyRouteContext): Promise<Response> {
  return proxyToBackend(request, context);
}

export async function DELETE(request: Request, context: ProxyRouteContext): Promise<Response> {
  return proxyToBackend(request, context);
}

export async function OPTIONS(): Promise<Response> {
  return new Response(null, {
    status: 204,
    headers: corsHeaders()
  });
}

async function proxyToBackend(request: Request, context: ProxyRouteContext): Promise<Response> {
  const { path } = await context.params;
  const incomingUrl = new URL(request.url);
  const backendUrl = new URL(`${BACKEND_API_BASE_URL}/${path.map(encodeURIComponent).join("/")}`);
  backendUrl.search = incomingUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store"
  });

  const responseHeaders = new Headers(response.headers);
  for (const [key, value] of Object.entries(corsHeaders())) {
    responseHeaders.set(key, value);
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders
  });
}

function corsHeaders(): Record<string, string> {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization"
  };
}
