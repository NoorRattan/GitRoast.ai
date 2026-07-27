# Production Verification

Session 6 is the live-deploy close-out pass. This file records what was actually verified and what is blocked by missing dashboard access or production secrets.

## Current production targets

| Service | Target | Status |
|---|---|---|
| Backend | `https://gitroast-api.onrender.com` | Not deployed. `GET /health` returns Render routing `404` with `x-render-routing: no-server`. |
| Frontend | `https://gitroast-ai-frontend.jnoorrattan.workers.dev` | Dashboard build/deploy retry reached OpenNext build and Worker asset upload. Custom domain remains blocked until the `gitroast.ai` zone exists in this Cloudflare account. |
| Card Worker | `https://card.gitroast.ai` | Not live. Cloudflare upload succeeded, but custom-domain route creation failed because Wrangler could not find a Cloudflare zone for `card.gitroast.ai`. |
| Card Worker preview | `https://gitroast-card-preview.jnoorrattan.workers.dev` | Live from Session 5 follow-up. Cache-key behavior verified on workers.dev only. |

## Repo-side production configuration completed

- Added `render.yaml` for the Render backend service.
- Pinned Python with `.python-version` and `PYTHON_VERSION=3.12.10`.
- Set Render health check path to `/health`.
- Declared required backend env vars from `app/core/config.py`: `GITHUB_PAT`, `UPSTASH_URL`, `UPSTASH_TOKEN`, `NEON_DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ALLOWED_ORIGINS`.
- Confirmed `ANTHROPIC_API_KEY` is not present in `Settings`.
- Set `ALLOWED_ORIGINS` to the intended production frontend origin, `https://gitroast.ai`; no wildcard is used.
- Added root `wrangler.jsonc` for the OpenNext frontend Worker on workers.dev.
- Added frontend Cloudflare scripts: `build:cloudflare`, `deploy`, and `preview`.
- Pointed the frontend default API base URL at `https://gitroast-api.onrender.com/api/v1`; local development can still override it with `NEXT_PUBLIC_API_BASE_URL`.
- Pointed the card Worker's `BACKEND_BASE_URL` at `https://gitroast-api.onrender.com/api/v1`.
- Added the card Worker custom-domain route for `card.gitroast.ai`; the route is configured in repo but not live until the `gitroast.ai` Cloudflare zone exists in this account and a production deploy succeeds.
- Attempted production card Worker deploy. Bundle upload succeeded with version `179cb6d8-fdd8-47d6-9efe-29edd4c35b45`, then route attachment failed: `Could not find zone for card.gitroast.ai. Make sure the domain is set up to be proxied by Cloudflare.`
- Retried the Cloudflare dashboard frontend build after correcting its commands. The build used `npm run build:cloudflare`, produced `.open-next/worker.js`, uploaded the Worker assets, and only failed when the old deploy command tried to attach `--domain gitroast.ai`.
- Updated the frontend dashboard deploy command and repo script to deploy the generated `.open-next/worker.js` artifact directly without a custom-domain flag. The custom domain must be attached later after the `gitroast.ai` zone exists in this Cloudflare account.

## Confirmed platform limits

- Render HTTP health checks must return `2xx` or `3xx` within 5 seconds.
- Render documentation currently states web services can take HTTP responses up to 100 minutes.
- Cloudflare Workers Free plan Worker-size limit is 3 MB after gzip compression.
- The card Worker dry-run remains under that limit: `Total Upload: 3360.82 KiB / gzip: 1190.83 KiB`.
- The OpenNext frontend Worker dry-run is also under that limit: `Total Upload: 3124.95 KiB / gzip: 677.44 KiB`.

## Frontend deploy command note

Cloudflare dashboard settings for the frontend Worker:

```text
Build command: npm run build:cloudflare
Deploy command: npm run deploy:direct
```

Do not use `npm run build` as the Cloudflare build command. It only creates `.next`, while the Worker deploy needs `.open-next/worker.js` from `opennextjs-cloudflare build`.

Do not use `npx wrangler deploy` as the Cloudflare deploy command for this repo. Wrangler detects the OpenNext project and delegates to the OpenNext deploy wrapper, which expects compiled OpenNext config and can fail with `Could not find compiled Open Next config, did you run the build command?`.

On this native Windows machine, the `opennextjs-cloudflare deploy` wrapper also fails before upload with:

`ERR_UNSUPPORTED_ESM_URL_SCHEME: On Windows, absolute paths must be valid file:// URLs. Received protocol 'n:'`

The generated artifact uploads when bypassing OpenNext autodetection. The direct deploy intentionally omits `--domain gitroast.ai` until that zone is available in this Cloudflare account:

```powershell
npm run deploy:direct
```

`npm run deploy` is now a convenience wrapper for `npm run build:cloudflare && npm run deploy:direct`.

## Blocked live checks

The in-app browser reaches `https://dashboard.render.com/login`, so no authenticated Render dashboard session is available. The process environment also has none of the required production secrets or Render API values.

Blocked until Render sign-in, production secret values, and the `gitroast.ai` Cloudflare zone exist in the authenticated account:

- Create or verify the Render `gitroast-api` web service.
- Set production `GITHUB_PAT`, `UPSTASH_URL`, `UPSTASH_TOKEN`, `NEON_DATABASE_URL`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`.
- Confirm the Render dashboard does not contain `ANTHROPIC_API_KEY`.
- Verify `/health` on the deployed Render service within the 5 second health-check window.
- Measure a real cold-path `POST /api/v1/audit` latency against the deployed backend.
- Deploy the frontend Worker to `https://gitroast.ai`.
- Add or transfer the `gitroast.ai` zone to the authenticated Cloudflare account and make it proxied, then redeploy the frontend Worker and card Worker routes.
- Redeploy the card Worker and attach `card.gitroast.ai`.
- Repeat the custom-domain `?v=1` / `?v=2` cache-key test on `card.gitroast.ai`.
- Run the full end-to-end smoke checklist against live services.

## Smoke checklist to run after deploy

- Search a real, small GitHub username and confirm a cold-path audit completes.
- Revisit the same username and confirm `cache_hit: true`.
- Search a beginner-account-shaped username and confirm `intensity_downgraded: true` displays the explanation.
- Confirm the share card image loads on the results page and at the direct `card.gitroast.ai` URL.
- Confirm an OG-preview checker renders a 1200x630 image.
- Opt out a test username; confirm `GET /api/v1/audit/{username}` returns `404` and `POST /api/v1/audit` returns `409`.
- Reverse the opt-out with `DELETE /api/v1/opt-out/{username}` and confirm the username can be re-audited.
- Log into the admin panel with production credentials and approve/reject a thin-finding review.
- Hit `POST /api/v1/audit` rapidly from one IP and confirm rate limiting eventually blocks, then recovers after the window.

## Portfolio priorities final state

1. Rate-limit/caching architecture: shipped in Sessions 1, 2, and 5; workers.dev cache-key behavior verified, live custom-domain verification blocked until `card.gitroast.ai` is attached.
2. Tone/safety calibration: shipped; live verification blocked until backend deploy.
3. Transparent deterministic scoring: shipped and covered by tests.
4. Legal/trust basics: opt-out and official-API-only are shipped; visible satire disclaimer still needs live UI verification.
5. Virality/shareable card: Worker shipped and workers.dev cache verified; production custom-domain verification blocked.
6. Retention: intentionally deferred; no user-facing history page exists.
7. LLM Phase 2 self-training: formally dropped because File 07 replaced external LLM generation with the local roast engine, leaving no Phase 1 LLM output stream to train on.
