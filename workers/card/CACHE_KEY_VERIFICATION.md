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

`27eda17d-833f-4d81-b29b-73d1424aa86f`

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

The preview environment still uses the placeholder `BACKEND_BASE_URL`, so this workers.dev probe validated the fallback PNG response path. Successful rendered card responses use the same `Content-Type` and `Cache-Control` headers.

## Custom-domain caveat

This confirms the cache-key mechanism on workers.dev only. It does not yet confirm behavior on the future custom domain; File 06 already flags that workers.dev and custom-domain behavior can differ.

Session 6 attempted to attach `card.gitroast.ai` by adding this production route:

```toml
[[routes]]
pattern = "card.gitroast.ai"
custom_domain = true
```

The production bundle upload succeeded with version `179cb6d8-fdd8-47d6-9efe-29edd4c35b45`, but route creation failed:

```text
Could not find zone for `card.gitroast.ai`. Make sure the domain is set up to be proxied by Cloudflare.
```

Custom-domain cache-key parity remains blocked until the authenticated Cloudflare account has an active, proxied `gitroast.ai` zone. After that, re-run the same `curl -I` checks against `https://card.gitroast.ai/card/<username>.png?v=1` and `?v=2`.
