# Production Verification

This file records the current public deployment targets for the repo. Stale custom-domain targets have been removed; the frontend is intentionally deployed on workers.dev.

## Current Production Targets

| Service | Target | Status |
|---|---|---|
| Frontend | `https://gitroast-ai-frontend.jnoorrattan.workers.dev` | Live on Cloudflare Workers. |
| Backend | `https://gitroast-ai.onrender.com` | Live on Render. `GET /health` returns `{"status":"ok"}`. |
| Card Worker preview | `https://gitroast-card-preview.jnoorrattan.workers.dev` | Live on workers.dev. Cache-key behavior has been verified with versioned `?v=` URLs. |

## Repo-Side Production Configuration

- Root `wrangler.jsonc` deploys the OpenNext frontend Worker to workers.dev with `workers_dev: true`.
- Frontend deploy command: `npm run deploy`, which runs `npm run build:cloudflare` and `npm run deploy:direct`.
- Direct frontend deploy command: `npm run deploy:direct`.
- Frontend server and browser requests call the Render API directly through `NEXT_PUBLIC_API_BASE_URL`.
- `render.yaml` defines the Render backend service and keeps secret values out of source with `sync: false`.
- Backend required env vars are `GITHUB_PAT`, `UPSTASH_URL`, `UPSTASH_TOKEN`, `NEON_DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ALLOWED_ORIGINS`.
- Optional centralized error reporting uses `SENTRY_DSN` on Render and `NEXT_PUBLIC_SENTRY_DSN` during the frontend build. Without them, backend exceptions still reach Render logs and frontend failures reach the error boundary and browser console.
- `ALLOWED_ORIGINS` is scoped to the live Workers.dev frontend origin.
- The card Worker preview uses `https://gitroast-ai.onrender.com/api/v1` as its backend base URL.
- Render runs `alembic upgrade head` before Uvicorn starts. Application startup does not mutate schema with `create_all`.
- Main-branch CI can deploy both Cloudflare Workers when the GitHub `production` environment contains `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
- Render deploys automatically from `main` through `render.yaml`.

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
- Latest frontend bundle check: `1.47 MiB gzip / 3.00 MiB`.
- The card Worker preview deploy remains under the Cloudflare Worker gzip limit.

## Smoke Checklist

- Search a real GitHub profile URL and confirm it redirects to the normalized username route.
- Confirm a cold-path audit completes.
- Revisit the same username and confirm cached audit behavior.
- Confirm the animated score visual renders without browser console errors.
- Confirm the share card image loads from the workers.dev card preview URL.
- Opt out a test username; confirm `GET /api/v1/audit/{username}` returns `404` and `POST /api/v1/audit` returns `409`.
- Reverse the opt-out with `DELETE /api/v1/opt-out/{username}` and confirm the username can be re-audited.
- Log into the admin panel directly at `/admin` with production credentials and approve/reject a thin-finding review.
- Hit `POST /api/v1/audit` rapidly from one IP and confirm rate limiting eventually blocks, then recovers after the window.
