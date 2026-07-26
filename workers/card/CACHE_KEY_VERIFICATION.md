# Card Worker Cache-Key Verification

The Worker intentionally uses header-based Cloudflare caching rather than `caches.default`:

`Cache-Control: public, max-age=21600, stale-while-revalidate=3600`

That keeps the implementation simple and lets Cloudflare's standard cache key behavior include the query string for `?v={schema_version}`. The required real-edge verification is:

1. Set `BACKEND_BASE_URL` for the preview environment to the deployed FastAPI base URL.
2. Deploy the preview Worker:
   `npx wrangler deploy --env preview`
3. Request the same username with two different schema versions:
   `curl -I "https://<preview-host>/card/<username>.png?v=1"`
   `curl -I "https://<preview-host>/card/<username>.png?v=2"`
4. Repeat both requests and confirm each URL is independently retrievable with `Content-Type: image/png`, the 6h cache-control header, and separate cache behavior for the two query strings.

Current local verification:

- `npx wrangler deploy --dry-run --outdir dist --env preview` succeeds.
- `npx wrangler whoami` reports no authenticated Cloudflare account.
- `npx wrangler deploy --temporary --env preview` reaches Cloudflare but cannot create the preview Worker on the temporary free account because the bundled `@resvg/resvg-wasm/index_bg.wasm` makes the Worker exceed that account's 1 MiB limit. Wrangler reported the largest dependency as `node_modules\@resvg\resvg-wasm\index_bg.wasm - 2420.51 KiB`.
- The same command also confirmed current Wrangler syntax for an unauthenticated temporary preview deploy is `wrangler deploy --temporary`.

Result: header-based `?v=` cache-key behavior is still pending real-edge verification because no preview URL could be created without an authenticated Cloudflare account/plan that allows this Worker size. The implementation intentionally has not added `caches.default`; once a deployable preview URL exists, run the four curl checks above and only add runtime-cache complexity if the header-based mechanism fails empirically.
