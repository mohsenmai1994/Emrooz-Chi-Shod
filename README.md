# Emrooz Chi Shod — Bale News Bot

Minimal, modular Python news bot. **The ONLY schedule is on cron-job.org.** GitHub Actions contains `workflow_dispatch` only: there is no `schedule`, `cron`, `sleep` or infinite loop in the application.

## Architecture

`cron-job.org` (every 5 minutes) → GitHub REST `workflow_dispatch` → GitHub Actions runs `python main.py` once → newest suitable RSS article → Bale channel → commit `state.json` after successful send.

This design requires **no VPS, Flask, web page, external Python packages or GitHub schedule**. GitHub is used to execute each triggered one-shot run, rather than as an always-on server.

## Repository files

- `main.py`: one-shot selection and publishing (at most one item)
- `feeds.py`: RSS/Atom parsing, image retrieval, deduplication fingerprints
- `bale.py`: formatted caption and Bale Bot API requests
- `config.py`: RSS URLs, topic keywords and environment settings
- `state.py`: history storage
- `state.json`: persistent posted-news fingerprints (committed automatically)
- `.github/workflows/publish.yml`: **manual/API-only execution, no scheduling**

## Setup (GitHub)

1. Create a repository with **default branch `main`**, and upload all files including `.github/workflows/publish.yml` and `state.json`.
2. In GitHub: **Settings → Secrets and variables → Actions → Secrets**, create:
   - `BALE_BOT_TOKEN` = your Bale bot token (keep private).
3. Under **Variables**, create:
   - `BALE_CHANNEL` = the **channel** username with `@`, e.g. `@your_news_channel` (not the bot username).
4. Make the bot an admin of the Bale channel with permission to post.
5. In **Actions**, select **Publish one news item** and click **Run workflow** once. Check the logs and channel. (This is a one-time manual test, not a GitHub schedule.)
6. The job must have permission to update `state.json`. The workflow already requests `contents: write`. If GitHub branch protection forbids bot commits, allow them or choose an unprotected state branch (requires changing the workflow).

## Cron-job.org (this is the ONLY scheduler)

Create a cron job with:

- **URL:** `https://api.github.com/repos/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY/actions/workflows/publish.yml/dispatches`
- **Request method:** `POST`
- **Request body (JSON):** `{"ref":"main"}`
- **Request headers:**
  - `Authorization: Bearer YOUR_GITHUB_FINE_GRAINED_PAT`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- **Interval:** Every **5 minutes** (e.g. 00, 05, 10, 15 ... every hour).
- **Success:** GitHub responds with **HTTP 204 No Content** for a successful dispatch by default. That only means the workflow was queued, NOT that a news post was published. Check GitHub Actions for the actual result.

### GitHub PAT (for cron-job.org only)

On GitHub, create a **fine-grained Personal Access Token** (Settings → Developer settings → Personal access tokens → Fine-grained tokens):

- Repository access: **Only selected repository** → this repo
- Repository permissions: **Actions: Read and write**; Metadata is automatically Read.
- Set an expiration and remember to renew it in cron-job.org.

Do **not** paste your Bale bot token into cron-job.org. Keep the GitHub PAT only in cron-job.org configuration, never in source code. Protect the cron-job.org account.

## Local preview (no token, no publishing)

```bash
python main.py --preview
```

For a one-shot local real send, set the environment variables `BALE_BOT_TOKEN` and `BALE_CHANNEL` and then run `python main.py`.

## Behavior

- The scheduler calls the workflow every five minutes, but **each execution checks once and exits**.
- Fetches RSS feeds from Mehr, ISNA, IRNA and YJC.
- Chooses **at most one** recent article based on date, economic keywords, and posted history.
- Fetches the **selected article page only** to extract a complete, short lead when RSS contains truncated text.
- Removes publisher datelines such as `یزد- ایرنا-` from the post body (the source credit remains).
- Uses full sentences instead of cutting at an arbitrary character count. If a reliable complete lead cannot be obtained, it omits the lead rather than publishing a broken phrase.
- Sends the image with caption when available, otherwise sends a text post.
- If no eligible new article exists, sends nothing.
- Posts a link to the source article and attributes the publisher.
- Commits `state.json` back to the repository only after Bale confirms posting. `concurrency` prevents overlapping GitHub workflow runs.
- Note: if Bale accepts a post but GitHub fails before saving the state commit, a later run *might* repeat it; exactly-once delivery cannot be guaranteed with two separate systems.

## Cost and limits

Every 5 minutes = **288 workflow dispatches/day** (~8,640 in 30 days). This can exceed included GitHub Actions minutes in a **private** repository. Standard GitHub-hosted Actions minutes in a **public** repository are generally free under GitHub billing rules, but check current fair-use and usage terms. GitHub can also delay job startup, so publication is not guaranteed exactly on the 5-minute boundary. If execution cost or GitHub run quotas become a problem, move the one-shot script to a real HTTPS service and let cron-job.org call that endpoint instead.

## Important

- Don't run `main.py` without the `--preview` flag locally unless you intend to publish.
- News content can be inaccurate; important or sensitive headlines deserve human review before publication.
- Source credit does not automatically grant image reuse rights. Use only images you have permission to republish.
- The Bale Bot API documentation is at https://docs.bale.ai/.
