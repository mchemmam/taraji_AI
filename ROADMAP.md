# Taraji AI — Roadmap

Ideas parked here so they don't get lost. Constraint for everything: **$0/month** — free tiers only (GitHub Actions/Pages, Gemini free tier ~20 req/day *per model* — hence the model chain in `settings.GEMINI_MODELS`; verified live 2026-07-18, Telegram Bot API, cron-job.org). Design rule that keeps us inside the Gemini quota: **at most one batched AI call per collection run** — new features should ride that existing call, or add at most one call per day.

## Shipped

- ✅ **2026-07-18** — Facebook auto-posting (code side): `distributors/facebook_page.py` posts to the Taraji Press Page via the Graph API; publication tracked per channel in `distribution_log`. Goes live once the Page is created and `FACEBOOK_PAGE_ID`/`FACEBOOK_PAGE_ACCESS_TOKEN` secrets are set (`python main.py facebook-setup` walks through it).
- ✅ **2026-07-17** — Photo posts: Telegram messages use the extracted article image (`sendPhoto` + caption, text fallback).
- ✅ **2026-07-17** — Failure alerting: workflow failures ping Telegram (`TELEGRAM_ALERT_CHAT_ID` secret optional, falls back to `TELEGRAM_CHAT_ID`).
- ✅ **2026-07-17** — Bilingual summaries: every article gets both a French and an Arabic summary from the same batched Gemini call.
- ✅ **2026-07-17** — Cross-language dedup: the AI batch marks within-batch duplicates (same story via two sources/languages) and stories already covered in the last 48h; both are rejected before posting.

## Next up (unlocks the public channel)

1. **Importance ranking** — add an `importance` field (breaking / normal / minor) to the batched Gemini call. Breaking gets a 🚨 immediate post; minor is held for the digest. This is the signal/noise fix the public channel needs.
2. **Daily digest** — one extra Gemini call per day composing a grouped "yesterday at EST" message (where the "minor" articles end up). Second cron-job.org job, or a time check inside the existing workflow.
3. **Switch `TELEGRAM_CHAT_ID` to `@taraji_news`** — config-only change, after output quality is validated in the test chat. Set `TELEGRAM_ALERT_CHAT_ID` to the private chat at the same time so failure alerts stay private.

## Planned

- **GitHub Pages dashboard** — Actions step exports the DB to JSON and deploys a static page (search, category/language filters, stats charts). The keep-every-row-forever retention policy exists for this. The exported JSON doubles as a free public API.
- **Match-day awareness** — pre-match reminders + full-time score posts. API-Football free tier (100 req/day) covers Tunisian Ligue 1 and CAF competitions; a handful of requests on match days fits.
- **More sources** — candidates: official EST site, club YouTube channel RSS (`youtube.com/feeds/videos.xml?channel_id=…`, no key needed). Noisy feeds are cheap to add: keyword filter + AI relevance check reject junk once and remember it.

## Stretch

- **Interactive Q&A bot** — fans ask the bot about recent news, Gemini answers from the article archive. Needs a webhook endpoint (Cloudflare Workers free tier is the usual answer) — more moving parts, only worth it if the channel gets traction.
- **Weekly recap** — one Gemini call every Sunday; cheap once digest machinery exists.
- **Season stats on the dashboard** — derived from the archive.

## Deliberately not doing

- **Per-article AI calls** (individual summarization/translation passes) — would blow the free-tier quota at 96 runs/day. Everything batches.
- **Twitter/X** — dropped 2026-07-15; no viable free access in 2026.
- **DB row deletion** — full article rows are kept forever for the archive/dashboard; only bulky text content is pruned after 30 days (see `GUIDE.md`).
