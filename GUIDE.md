# Taraji AI — User Guide

A plain-language reference for how the system actually works today. For the original design/roadmap doc see `PLAN.md`; for dev setup commands see `README.md`. This doc is the "remind me how this works" one.

---

## What it does

Watches the internet for news about Espérance Sportive de Tunis (French, Arabic, English), filters out anything irrelevant, summarizes and categorizes what's left with AI, and posts new articles to a Telegram chat. Runs unattended on GitHub Actions — no server to maintain, no monthly cost.

---

## The pipeline (`python main.py collect`)

Each run does 7 steps, in order (see `main.py:cmd_collect`):

1. **Collect** — pulls articles from Google News (`collectors/google_news.py`) and a curated list of RSS feeds (`collectors/rss_collector.py`, feed list in `config/settings.py` `RSS_FEEDS` — currently Nessma TV Sport (AR + FR) and Mosaïque FM).
2. **Keyword filter** — cheap text match before any network/AI cost. Rules live in `config/keywords.json`, checked in this order:
   - `exact`: unambiguous club names per language ("Espérance de Tunis", "الترجي التونسي", etc.). These always match — negative keywords can NOT veto them, otherwise derby coverage ("Espérance de Tunis bat le Club Africain") would be dropped. A wrongly-kept article still gets caught by the AI relevance check in step 7.
   - `negative`: vetoes everything below this point — lookalikes such as other Tunisian clubs (Club Africain, Étoile du Sahel, CSS Sfax, Espérance de Zarzis...), tennis player Ons Jabeur, actress Taraji P. Henson, and generic football noise (Messi, Ronaldo, Wimbledon) that would otherwise slip through fuzzy matching.
   - `exact_ambiguous`: short names that are substrings of lookalikes — bare "الترجي" also appears in "الترجي الجرجيسي" (Espérance de Zarzis), so it only counts if no negative keyword fired.
   - `contextual`: ambiguous terms like "EST" or "Taraji" only count if a football-related word is nearby.
   - fuzzy: typo-tolerant match on the full club names (85% similarity).

   **Gotcha (hit 2026-07-16):** negative entries need every language variant, not just French/English — "Espérance de Zarzis" was excluded in Latin script but not its Arabic name "الترجي الجرجيسي", so Arabic articles about that club matched "الترجي" and slipped through for a while. When adding a new negative keyword, add the Arabic form too if one exists. Sanity-check any keyword change with `python scripts/check_keywords.py "<headline>"`.
3. **Dedup against DB** — drops URLs already stored (and URLs the AI previously rejected, kept in the `rejected_urls` table), so nothing gets re-processed on every 15-min run.
4. **Extract content** — fetches full article text from the URL (needed for a decent AI summary, not just the RSS blurb).
5. **Dedup again** — after following redirects, catches the same story reached via two different URLs (e.g. Google News link + the RSS link).
6. **Detect language** — fr / ar / en, stored per article.
7. **AI processing** — one **batched** Gemini call (`gemini-2.5-flash`) per run does relevance double-check, staleness check, categorization, and summary together. Batching everything into a single request is deliberate: the free tier is roughly 250 requests/day, and per-article calls would burn through that fast. Falls back to rule-based classification if Gemini is unavailable. Articles the AI rejects (irrelevant or stale) are remembered in the `rejected_urls` table so they aren't re-extracted and re-judged on every subsequent run.

Then everything new gets stored in `data/taraji_ai.db` (SQLite). Runs that store something also **prune**: full article text older than 30 days (`CONTENT_RETENTION_DAYS`) is blanked — the text is only needed once, to generate the summary — and rejected URLs older than 30 days are dropped. Every article row (title, summary, category, URL, dates) is kept forever for the future archive/dashboard; this just caps the growth of the git-committed database. Deliberately no `VACUUM`: rewriting the whole file would defeat git's delta compression.

### Categories
Defined in `config/settings.py` (`CATEGORIES`): ⚽ match, 💼 transfer, 🏥 injury, 💬 statement, 💰 finance, 📰 other. Each has French/Arabic/English display names and its own emoji, used when formatting Telegram messages.

---

## Distribution (`python main.py distribute`)

Sends every unpublished article to a Telegram chat via `distributors/telegram_bot.py` — plain HTTPS calls to the Bot API, no SDK. One message per article (throttled to 1 every 3 seconds, under Telegram's ~20/min limit), formatted with the category emoji, title, summary, source, and a link.

- **Bot**: `@taraji_ai_news_bot`, created via @BotFather (2026-07-16).
- **Target chat**: currently your private test chat (`TELEGRAM_CHAT_ID`) — deliberately *not* the public channel yet, so output quality gets validated before anyone else sees it.
- **Public channel** (`@taraji_news`) is the planned destination once the test output looks right — just a config change (swap `TELEGRAM_CHAT_ID`), no code change.
- `python main.py telegram-setup` verifies the bot token and lists chat IDs the bot has seen — use it whenever you need to (re)discover a chat ID (e.g. switching to the channel later).

---

## Automation

**GitHub Actions** (`.github/workflows/collect.yml`) runs `collect` then `distribute` on a schedule, and commits `data/taraji_ai.db` back to `main` if anything new was found (so state persists between runs without a database server).

**Important quirk:** GitHub's built-in `schedule:` cron trigger is "best effort" and — especially for a public repo asking for 15-minute frequency — GitHub silently drops most of the ticks. In practice this meant runs landing every ~1.5–2.5 hours instead of every 15 minutes, even though the cron expression (`7,22,37,52 * * * *`) was correct.

**The fix (2026-07-16):** a free external cron service, **cron-job.org**, hits the GitHub REST API every 15 minutes to fire a `workflow_dispatch` event instead of relying on `schedule`:
```
POST https://api.github.com/repos/mchemmam/taraji_AI/actions/workflows/collect.yml/dispatches
Authorization: Bearer <fine-grained PAT, Actions:read-and-write only>
Body: {"ref":"main"}
```
`workflow_dispatch`-triggered runs aren't subject to the same throttling, so this reliably gets real 15-minute cadence. **The PAT expires 2026-10-14** — when it does, the cron-job.org pings will start failing (visible in that service's job history), and a new fine-grained token needs to be generated and swapped into the cron-job.org header.

To sanity-check cadence at any time:
```bash
gh run list --workflow=collect.yml --repo mchemmam/taraji_AI --limit 10 \
  --json createdAt,status,conclusion,event
```
Runs with `event=workflow_dispatch` are the cron-job.org pings; `event=schedule` are GitHub's native (unreliable) trigger, kept as a redundant backup in the workflow file.

---

## Where the secrets live

| Secret | Local (`.env`) | GitHub Actions | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | repo secret | AI summarization/classification |
| `TELEGRAM_BOT_TOKEN` | ✅ | repo secret | Bot auth for posting |
| `TELEGRAM_CHAT_ID` | ✅ | repo secret | Where messages get sent (test chat) |
| cron-job.org's GitHub PAT | — | lives only in cron-job.org's job config | Triggers `workflow_dispatch` every 15 min |

Check what's set on GitHub with `gh secret list --repo mchemmam/taraji_AI`.

---

## Everyday commands

```bash
python main.py init              # create the DB schema (one-time)
python main.py collect            # run the full pipeline once
python main.py collect --test     # same, but prints sample results
python main.py distribute         # push unpublished articles to Telegram
python main.py telegram-setup     # verify bot token, list chat IDs
python main.py stats              # article counts by category/language
```

Dev utilities live in `scripts/`: `inspect_articles.py` (browse/inspect stored articles), `view_articles.py` (recent summaries), `quick_queries.sh` (SQL snapshots), `check_keywords.py` (test the keyword filter against a headline), `debug_filter.py` (live collection + filter trace).

Manually kick off a real run on GitHub (bypassing the 15-min wait): `gh workflow run collect.yml --repo mchemmam/taraji_AI`.

---

## Cost

$0/month. Google News + RSS are free with no key. Gemini free tier (~250 req/day for `gemini-2.5-flash`) comfortably covers one batched call per 15-min run. Telegram Bot API is free and unlimited. GitHub Actions is free because the repo is public. cron-job.org's free tier covers a single job pinging every 15 min.

---

## Not built yet / open threads

- **Daily digest** (grouped summary message) and a **GitHub Pages dashboard** for browsing the archive — designed in `PLAN.md` but not implemented.
- **Facebook auto-posting** — parked as a concrete plan in `PLAN.md` ("Facebook & Twitter (Future)" section): Graph API, long-lived Page token, no App Review needed since it's our own Page.
- **Twitter/X** — dropped (2026-07-15): official free API gone, third-party APIs cost money.
- **Switch to the public `@taraji_news` channel** — pending validation of test-chat output quality.
