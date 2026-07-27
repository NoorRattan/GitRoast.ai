# Card Worker Cache-Key Verification

The Worker uses Cloudflare Workers Caching with cacheable response headers, not `caches.default`:

`Cache-Control: public, max-age=21600, stale-while-revalidate=3600`

`wrangler.toml` must keep Workers Caching enabled:

```toml
[cache]
enabled = true
```

That lets Cloudflare cache Worker-generated `GET` and `HEAD` responses and lets the standard Worker cache key include the request path and query string for `?v={schema_version}`.

## Size-limit correction

The earlier unauthenticated preview failure was caused by the temporary preview account's 1 MiB upload limit. That is not the real Workers Free plan deploy limit.

Cloudflare's Workers Free plan limit is 3 MB after gzip compression. This Worker dry-run reports:

`Total Upload: 3360.82 KiB / gzip: 1190.83 KiB`

So the authenticated Free plan deploy is comfortably under the real 3 MB gzip limit.

## workers.dev result

Authenticated deploy command:

`npx wrangler deploy --env preview`

Deployed URL:

`https://gitroast-card-preview.jnoorrattan.workers.dev`

Version ID:

`45c6b7d2-c070-4657-bcdb-4ea7e1134881`

Probe commands:

```bash
curl -I "https://gitroast-card-preview.jnoorrattan.workers.dev/card/octocat.png?v=1"
curl -I "https://gitroast-card-preview.jnoorrattan.workers.dev/card/octocat.png?v=2"
```

Observed result after initial misses:

```text
/card/octocat.png?v=1
HTTP/1.1 200 OK
Content-Type: image/png
CF-Cache-Status: HIT
Age: 5
Cache-Control: public, max-age=21600, stale-while-revalidate=3600

/card/octocat.png?v=2
HTTP/1.1 200 OK
Content-Type: image/png
CF-Cache-Status: HIT
Age: 4
Cache-Control: public, max-age=21600, stale-while-revalidate=3600
```

The first request to each URL returned `CF-Cache-Status: MISS`, and repeated requests to both versioned URLs independently reached `HIT`. This confirms `?v=1` and `?v=2` are separate cache entries on workers.dev.

The preview environment now uses `https://gitroast-ai.onrender.com/api/v1` as `BACKEND_BASE_URL`, so the workers.dev endpoint can render cards from the live backend when card data is available. Fallback PNG responses and rendered card responses use the same `Content-Type` and `Cache-Control` headers.

## Custom-domain status

No card custom domain is configured in this repo. The public, verified card endpoint is the workers.dev preview Worker:

`https://gitroast-card-preview.jnoorrattan.workers.dev`

The cache-key mechanism has been verified on workers.dev only.
