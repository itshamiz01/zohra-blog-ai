# Zohra Reddit Opportunity & Referral Engine — Operational Runbook

## 1. Configuration & Environment Variables

All settings integrate with Zohra's unified `Settings` model (`app/core/config.py`).

| Variable | Default | Purpose |
|---|---|---|
| `REDDIT_ENABLED` | `false` | Master toggle for the entire Reddit integration |
| `REDDIT_DISCOVERY_ENABLED` | `true` | Allows periodic ingestion and scanning of monitored subreddits |
| `REDDIT_RESPONSE_GENERATION_ENABLED` | `false` | Enables LLM generation of draft answers for approved articles |
| `REDDIT_POSTING_ENABLED` | `false` | **Safety Lock**: Prevents remote comment submission to Reddit |
| `REDDIT_AUTONOMY_MODE` | `"DISCOVERY_ONLY"` | Operational tier: `OFF`, `DISCOVERY_ONLY`, `DRAFT_RESPONSES`, `APPROVAL_REQUIRED`, `AUTO_LOW_RISK` |
| `REDDIT_CLIENT_ID` | `""` | Reddit OAuth Application ID (optional for public read-only discovery) |
| `REDDIT_CLIENT_SECRET` | `""` | Reddit OAuth Secret (strictly redacted from all logs and traces) |
| `REDDIT_USER_AGENT` | `"ZohraResearchBot/1.0"` | Standard compliant User-Agent identifier |
| `REDDIT_MAX_COMMENTS_PER_DAY` | `10` | Daily global publishing velocity cap per site |
| `REDDIT_MAX_LINKED_COMMENTS_PER_DAY`| `2` | Conservative daily quota on comments containing resource links |
| `REDDIT_MIN_HOURS_BETWEEN_SUBREDDIT_POSTS` | `2` | Minimum interval before engaging in the same community again |

---

## 2. Autonomy Policy & Safety Tiers

To safeguard community trust and prevent account suspension, the engine enforces strict autonomy tiers:

1. **`OFF`**: All Reddit activity stopped.
2. **`DISCOVERY_ONLY` (Default Production State)**:
   - Scans subreddits for questions.
   - Extracts intent and scores content opportunities.
   - Feeds the website research and editorial pipeline.
   - Generates no Reddit response drafts.
3. **`DRAFT_RESPONSES`**:
   - Generates helpful, standalone Reddit-native answers as internal drafts.
   - Submits zero comments to Reddit.
4. **`APPROVAL_REQUIRED`**:
   - Generates response drafts.
   - Verifies subreddit rules and anti-spam constraints.
   - Queues responses in the Zohra Command Center for human operator sign-off.
   - Comments are submitted only after explicit owner approval.
5. **`AUTO_LOW_RISK`**:
   - Strictly reserved for mature accounts and highly verified communities where self-promotion is explicitly permitted.
   - Never enabled by default.

---

## 3. Command Center Operator Workflow

1. **Accessing Reddit Radar**:
   - Open the Zohra Command Center at `http://localhost:8000/static/console.html`.
   - Click the **Reddit Radar** tab on the navigation bar.
2. **Monitoring Ingested Questions**:
   - Review the **Content Opportunities** section.
   - Check the **Opportunity Score**, **Recommended Action** (`create_new_article`, `update_existing_article`, etc.), and **Why Selected** rationale.
3. **Reviewing Response Drafts in the Approval Queue**:
   - Inspect the proposed response and rule status.
   - If the response includes a link:
     - Review the destination URL and link rationale.
     - Click **Approve** to authorize submission (if live posting is enabled).
     - Click **Publish Without Link** to immediately strip the URL and approve the standalone answer.
     - Click **Reject** to dismiss the draft.
4. **Running an Interactive Dry Run**:
   - Click **Run End-to-End Dry Run**.
   - Input any real Reddit question (e.g. *"What are the best open-source tools for building AI agents?"*).
   - Review the complete 13-stage execution trace, proposed standalone response, and posting safety status.

---

## 4. Troubleshooting & FAQ

### Issue: Rate limits encountered during public JSON discovery
- **Cause**: Reddit public endpoints enforce strict rate limits per IP address (approximately 60 requests/minute).
- **Resolution**:
  1. Increase discovery polling interval to 15–30 minutes.
  2. Configure `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env` to switch to authenticated OAuth rate limits (up to 1,000 requests/minute).

### Issue: All drafted responses default to `Would include link: False`
- **Cause**: The community's rules are unconfirmed (`rule_status = "rule_status_unknown"`) or the subreddit prohibits self-promotion.
- **Resolution**: This is the intended fail-safe behavior. To permit links in a specific community, navigate to the **Community Policies** tab and verify the subreddit's external link rules.

### Issue: Comments failing Anti-Spam Guard check
- **Cause**: Content hash matched a previously submitted comment, or the daily limit of 10 comments has been reached.
- **Resolution**:
  1. Inspect `RedditAntiSpamGuard` logs.
  2. Verify that response templates are sufficiently varied.
  3. Wait for the velocity cooldown window (24 hours) or adjust `REDDIT_MAX_COMMENTS_PER_DAY` in `.env`.
