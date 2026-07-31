# Production Verification

This file records the current public deployment targets for the repo. Stale custom-domain targets have been removed; the frontend is intentionally deployed on workers.dev.

## Current Production Targets

| Service | Target | Status |
|---|---|---|
| Frontend | `https://gitroast-ai-frontend.jnoorrattan.workers.dev` | Live on Cloudflare Workers. |
| API gateway | `https://gitroast-api-gateway-preview.jnoorrattan.workers.dev/api/v1` | Only public entry point for protected API routes. |
| Backend | `https://gitroast-ai.onrender.com` | Live on Render. `GET /health` returns `{"status":"ok"}`. |
| Card Worker preview | `https://gitroast-card-preview.jnoorrattan.workers.dev` | Live on workers.dev. Cache-key behavior has been verified with versioned `?v=` URLs. |

Latest verified frontend Worker version: `8334444a-d5ea-4bb3-8a7f-9a56466126d4`.

## Repo-Side Production Configuration

- Root `wrangler.jsonc` deploys the OpenNext frontend Worker to workers.dev with `workers_dev: true`.
- Frontend deploy command: `npm run deploy`, which runs `npm run build:cloudflare` and `npm run deploy:direct`.
- Direct frontend deploy command: `npm run deploy:direct`.
- Frontend server and browser requests call the Cloudflare API gateway through `NEXT_PUBLIC_API_BASE_URL`; the gateway removes client-supplied forwarding headers and attaches the trusted client identity and private gateway secret upstream.
- `render.yaml` defines the Render backend service and keeps secret values out of source with `sync: false`.
- Backend required env vars are `GITHUB_PAT`, `UPSTASH_URL`, `UPSTASH_TOKEN`, `NEON_DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `GATEWAY_SHARED_SECRET`, and `ALLOWED_ORIGINS`.
- Optional centralized error reporting uses `SENTRY_DSN` on Render and `NEXT_PUBLIC_SENTRY_DSN` during the frontend build. Without them, backend exceptions still reach Render logs and frontend failures reach the error boundary and browser console.
- `ALLOWED_ORIGINS` is scoped to the live Workers.dev frontend origin.
- The card Worker preview uses the Cloudflare API gateway as its backend base URL.
- Render runs `alembic upgrade head` before Uvicorn starts. Application startup does not mutate schema with `create_all`.
- Main-branch CI deploys the gateway, frontend, card Worker, then Render in that order when the GitHub `production` environment contains `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `GATEWAY_SHARED_SECRET`, and `RENDER_DEPLOY_HOOK`.
- Set `GATEWAY_SHARED_SECRET` in Render before triggering its deploy hook. The backend intentionally fails fast if a required variable is absent.

## Cloudflare Build Notes

Cloudflare dashboard settings for the frontend Worker:

```text
Build command: npm run build:cloudflare
Deploy command: npm run deploy:direct
```

Do not use `npm run build` as the Cloudflare build command. It only creates `.next`, while the Worker deploy needs `.open-next/worker.js` from `opennextjs-cloudflare build`.

Do not use `npx wrangler deploy` as the Cloudflare deploy command for this repo. Wrangler detects the OpenNext project and delegates to the OpenNext deploy wrapper, which expects compiled OpenNext config and can fail with `Could not find compiled Open Next config, did you run the build command?`.

Do not use bare `wrangler deploy ...` as the Cloudflare dashboard deploy command. Cloudflare's build shell did not expose bare `wrangler` on PATH; `npm run deploy:direct` works because npm exposes `node_modules/.bin/wrangler`.

On native Windows, the `opennextjs-cloudflare deploy` wrapper can fail before upload with:

`ERR_UNSUPPORTED_ESM_URL_SCHEME: On Windows, absolute paths must be valid file:// URLs. Received protocol 'n:'`

The generated artifact uploads when bypassing OpenNext autodetection:

```powershell
npm run deploy:direct
```

`npm run build:cloudflare` also runs `scripts/patch-opennext-worker.mjs` after OpenNext builds. This keeps the generated Worker from throwing on OpenNext's empty `process.chdir("")` call in the Cloudflare runtime.

## Confirmed Platform Limits

- Cloudflare Workers Free plan Worker-size limit is 3 MB after gzip compression.
- Latest frontend deploy: `1093.10 KiB` gzip, under the `3.00 MiB` limit.
- Latest card Worker preview deploy: `1190.96 KiB` gzip, under the `3.00 MiB` limit.

## Smoke Checklist

- Search a real GitHub profile URL and confirm it redirects to the normalized username route.
- Confirm a cold-path audit completes.
- Revisit the same username and confirm cached audit behavior.
- Confirm the score visual renders with its readable fallback and without browser console errors.
- Confirm the share card image loads from the workers.dev card preview URL.
- Opt out a test username; confirm `GET /api/v1/audit/{username}` returns `404` and `POST /api/v1/audit` returns `409`.
- Reverse the opt-out with `DELETE /api/v1/opt-out/{username}` and confirm the username can be re-audited.
- Log into the admin panel directly at `/admin` with production credentials and approve/reject a thin-finding review.
- Hit `POST /api/v1/audit` rapidly through the API gateway from one IP and confirm `RateLimit-*` / `Retry-After` headers appear when the limit is reached, then recover after the window.
- From two different real networks, repeat the gateway test and confirm independent rate-limit buckets. Client-supplied `CF-Connecting-IP` must not affect the result.
- Confirm a direct protected Render API request returns the shared `403` error envelope. Never place the gateway secret in a browser, curl command, issue, or log.
