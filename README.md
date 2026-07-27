# GitRoast.ai

Rule-based GitHub profile audits with deterministic scoring, local roast generation, and shareable profile cards.

## Links

| Service | Link | Verified status |
| --- | --- | --- |
| Frontend | https://gitroast-ai-frontend.jnoorrattan.workers.dev | Live on Cloudflare Workers |
| Example card image | https://gitroast-card-preview.jnoorrattan.workers.dev/card/torvalds.png?v=1 | Live on the card preview worker |
| Production verification | docs/production-verification.md | Checked-in deployment notes |
| Card cache verification | workers/card/CACHE_KEY_VERIFICATION.md | Checked-in cache-key verification notes |

## Not Live Yet

These targets are intentionally not linked above because they are not currently working:

- `gitroast.ai` does not resolve yet.
- `card.gitroast.ai` does not resolve yet.
- `gitroast-api.onrender.com` currently returns Render `404 no-server`.
- The repository URL is not listed as a public external link because unauthenticated checks return `404`.

## Deployment Notes

- The Cloudflare frontend dashboard should use `npm run build:cloudflare` and `npm run deploy:direct`.
- The frontend is currently live on workers.dev.
- The backend and full end-to-end audit flow still depend on a live Render service with production environment variables.
