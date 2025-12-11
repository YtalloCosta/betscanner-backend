# BetScanner - Surebet backend (Playwright-ready)

## URL
(será disponibilizada pelo Railway após deploy)

## Endpoints
- GET `/health` (public)
- GET `/odds` (requires `X-API-Key`)
- POST `/scrape` (requires `X-API-Key`)
- GET `/surebets` (requires `X-API-Key`)
- WebSocket `/ws/updates` (real-time updates)

## Auth
Header: `X-API-Key: <value set in Railway variable BETSCANNER_API_KEY>`

## Deploy (Railway)
1. Push repo to GitHub (this repo).
2. Railway connected to repo will auto-build using Dockerfile.
3. Add Railway Variable: `BETSCANNER_API_KEY`
4. Optionals: `SCRAPE_INTERVAL_SECONDS`, `DEFAULT_DAYS_AHEAD`

## Notes
- Playwright scrapers may require proxies and captcha solutions in production.
- For production use Redis / Postgres instead of in-memory store.
