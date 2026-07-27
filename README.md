# GitRoast.ai

Rule-based GitHub profile audits with deterministic scoring, local roast generation, and shareable profile cards.

## Links

| Service | Link | Status |
| --- | --- | --- |
| GitHub repository | https://github.com/NoorRattan/GitRoast.ai | Source of truth |
| Frontend | https://gitroast-ai-frontend.jnoorrattan.workers.dev | Live on Cloudflare Workers |
| Frontend custom domain | https://gitroast.ai | Planned; blocked until the Cloudflare zone is attached |
| Backend | https://gitroast-api.onrender.com | Render target; not verified live yet |
| Backend API base | https://gitroast-api.onrender.com/api/v1 | Used by the frontend and card worker when the backend is live |
| Card worker preview | https://gitroast-card-preview.jnoorrattan.workers.dev | Live preview; workers.dev cache-key behavior verified |
| Card worker custom domain | https://card.gitroast.ai | Planned; blocked until the Cloudflare zone is attached |
| Production verification | docs/production-verification.md | Current deployment notes and blockers |
| Card cache verification | workers/card/CACHE_KEY_VERIFICATION.md | Card cache-key verification notes |

## Deployment Notes

- The Cloudflare frontend dashboard should use `npm run build:cloudflare` and `npm run deploy:direct`.
- The frontend is currently live on workers.dev. The `gitroast.ai` custom domain is not attached in this Cloudflare account yet.
- The backend and full end-to-end audit flow still depend on the Render service being live with production environment variables.
