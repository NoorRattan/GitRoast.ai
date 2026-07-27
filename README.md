# GitRoast.ai

Rule-based GitHub profile audits with deterministic scoring, local roast generation, and shareable profile cards.

## Links

| Service | Link | Verified status |
| --- | --- | --- |
| Source | https://github.com/NoorRattan/GitRoast.ai | Public repository |
| Frontend | https://gitroast-ai-frontend.jnoorrattan.workers.dev | Live on Cloudflare Workers |
| Backend health | https://gitroast-ai.onrender.com/health | Live on Render |
| Example card image | https://gitroast-card-preview.jnoorrattan.workers.dev/card/torvalds.png?v=1 | Live on the card preview worker |
| Production verification | docs/production-verification.md | Checked-in deployment notes |
| Card cache verification | workers/card/CACHE_KEY_VERIFICATION.md | Checked-in cache-key verification notes |

## Deployment Notes

- The Cloudflare frontend dashboard should use `npm run build:cloudflare` and `npm run deploy:direct`.
- The frontend is intentionally deployed on workers.dev; no frontend custom domain is configured in this repo.
- The backend and full end-to-end audit flow still depend on a live Render service with production environment variables.
