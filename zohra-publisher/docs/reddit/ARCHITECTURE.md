# Zohra Reddit Opportunity & Referral Engine — Architecture Specification

## 1. Executive Summary & Design Philosophy
The **Zohra Reddit Opportunity & Referral Engine** is a first-class extension of the autonomous publishing platform **Zohra Blog AI**. It is designed with one unwavering principle:

> **Usefulness First — Not a Link Farm or Spam Bot.**
> Reddit is a real-user question discovery source, audience research channel, content opportunity radar, and community engagement mechanism. Website links are never automatically forced; Reddit answers provide standalone value regardless of whether a link is permitted or present.

The engine automates the entire lifecycle:
1. Identifying high-intent real-world user queries from targeted subreddits.
2. Filtering noise, memes, rants, and spam deterministically before invoking LLMs.
3. Grouping related questions into thematic clusters (preventing fragmented, thin articles).
4. Evaluating opportunity scores and determining strategic action (`create_new_article`, `update_existing_article`, `add_faq`, `answer_reddit_only`, `watch`, `reject`).
5. Handing off qualified opportunities to the existing Zohra Research & Writing Engine (`openai/gpt-4o-mini`).
6. Generating standalone, authentic, Reddit-native responses with transparent affiliation disclosure.
7. Checking community rules (defaulting to zero links on unknown rules).
8. Passing through an Anti-Spam Guard (SHA-256 duplicate content hash, velocity caps, SSRF prevention).
9. Routing through a Human Approval Queue before any publishing action.
10. Attributing referral traffic via UTM parameters (`utm_source=reddit`, `utm_medium=community`, `utm_campaign=...`).
11. Closing the loop with the Learning Engine to continuously improve topic selection.

---

## 2. End-to-End Architectural Pipeline

```text
                                REDDIT
                                   │
                                   ▼
                       [ RedditProvider ]
               (Public JSON / OAuth API Boundary)
                                   │
                                   ▼
                    [ RedditQuestionScanner ]
               (Topic/Keyword & Subreddit Monitor)
                                   │
                                   ▼
                   [ Deterministic Filter & Dedup ]
                  (Jaccard similarity, post ID check)
                                   │
                                   ▼
                    [ RedditQuestionClassifier ]
              (Direct Question, Advice, Problem, etc.)
                                   │
                                   ▼
                     [ RedditRelevanceScorer ]
               (Topical, Audience, Evergreen, etc.)
                                   │
                                   ▼
                   [ RedditQuestionClusterer ]
              (Parent Topics & Canonical Problems)
                                   │
                                   ▼
                   [ RedditOpportunityEngine ]
            (CREATE, UPDATE, ADD_FAQ, ANSWER_ONLY)
                                   │
                                   ▼
               ┌───────────────────────────────────────┐
               │    Existing Zohra Engine Handoff      │
               │  - Research Engine & Evidence Package │
               │  - SEO Intelligence & Blueprints      │
               │  - OpenAI/OpenRouter Provider         │
               │  - Editorial Audit & Fact-Check       │
               │  - Publishing Engine (Site Article)   │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                      [ RedditResponseWriter ]
                 (Standalone native helpful answer)
                                   │
                                   ▼
                     [ SubredditRuleChecker ]
             (Verifies rules; default to NO_LINK)
                                   │
                                   ▼
                      [ RedditAntiSpamGuard ]
             (SHA-256 hash, SSRF check, rate caps)
                                   │
                                   ▼
                    [ Human Approval Queue ]
             (Review, Strip Link, Edit, Approve)
                                   │
                                   ▼
                     [ Safe Posting Gate ]
               (DISABLED / DRY_RUN_ONLY initially)
                                   │
                                   ▼
                   [ Attributable UTM Link ]
                                   │
                                   ▼
                   [ RedditReferralTracker ]
                                   │
                                   ▼
                   [ RedditLearningEngine ]
               (Refines future opportunity radar)
```

---

## 3. Core Subsystems

### 3.1 Reddit Provider Abstraction (`app/reddit/provider.py`)
- Clean interface: `discover_posts()`, `fetch_post()`, `get_community_rules()`, `submit_comment()`, `health_check()`.
- Implements credential redaction in `__repr__` to prevent API key leaks into exception logs or traces.
- Supports both read-only unauthenticated public JSON endpoints and OAuth client credentials.
- Parses Reddit rate limit response headers (`x-ratelimit-remaining`, `x-ratelimit-reset`).

### 3.2 Question Classifier & Intent Extraction (`app/reddit/classifier.py`)
- **Deterministic Heuristics First**: Detects punctuation (`?`), 5W1H interrogative prefixes (`how`, `why`, `what`, `can`, etc.), and structural noise (`[rant]`, memes, short texts) without expensive LLM calls.
- **LLM Intent Extractor**: Uses `openai/gpt-4o-mini` with strict system prompting isolating untrusted Reddit text inside explicit XML data boundaries (`<untrusted_reddit_content>`).

### 3.3 Relevance & Opportunity Scoring (`app/reddit/relevance.py`, `app/reddit/opportunity.py`)
- **Multi-Dimensional Relevance**:
  - Topical overlap with configured site topics
  - Target audience alignment
  - Question clarity and specificity
  - Answerability and information gain potential
  - Evergreen value vs. transient noise
- **Opportunity Actions**:
  - `CREATE_NEW_ARTICLE`: High score (>=65), strong search gap, no existing coverage.
  - `UPDATE_EXISTING_ARTICLE`: High relevance to existing published article with missing subquestions.
  - `ADD_FAQ`: Narrow query suitable for an accordion/FAQ section in an existing article.
  - `ANSWER_REDDIT_ONLY`: Community-specific advice or conversational query not justifying a 2,000-word standalone blog post.
  - `WATCH`: Emerging discussion requiring monitoring before content commitment.
  - `REJECT`: Off-topic, spam, or low-quality query.

### 3.4 Question Clustering (`app/reddit/clustering.py`)
- Prevents thin-content proliferation by clustering related questions around canonical problems.
- Example: 4 separate questions about student AI use coalesce into one authoritative pillar article (*"Responsible AI Use for Students"*).

### 3.5 Zohra Research & Editorial Handoff (`app/reddit/handoff.py`)
- Bridges `RedditOpportunity` into Zohra's `ContentOpportunityPackage`.
- Preserves full lineage: `reddit_question_id`, cluster topics, subquestions, and target search intent.
- Leverages Zohra's existing `EditorialAuditEngine` and `FactVerificationEngine` before publication.

### 3.6 Reddit Response Writer (`app/reddit/response_writer.py`)
- Generates natural, helpful, conversational answers tailored for Reddit readers.
- **Strict Prohibition**: No corporate marketing buzzwords, no fake testimonials ("I used this and loved it"), and no clickbait teasers.
- Complete standalone value: readers receive the full solution without clicking external links.
- Conditional transparent attribution: includes contextual references only when permitted by subreddit rules.

### 3.7 Subreddit Rule Engine (`app/reddit/rules.py`)
- Queries `/r/{subreddit}/about/rules.json`.
- Enforces safety: if rule status is `RULE_STATUS_UNKNOWN` or confidence is low, external links and promotional content are strictly forbidden (`NO_LINK`).

### 3.8 Anti-Spam Guard & Safety Gate (`app/reddit/anti_spam.py`)
- **SHA-256 Content Hashing**: Prevents posting duplicate or near-identical comments.
- **Velocity Limits**: Configurable caps (e.g., max 10 comments/day, max 2 linked comments/day, min 15 minutes between actions).
- **Subreddit Cooldowns**: Enforces 2-hour minimum spacing per community.
- **SSRF Defense**: Validates destination URLs against private IP blocks (`127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`, `192.168.0.0/16`) and requires HTTP 200 before approval.

### 3.9 Human Approval Queue (`app/reddit/approval.py`)
- Complete operator governance via the Zohra Command Center UI (`console.html`).
- Actions: `Approve`, `Reject`, `Publish Without Link` (strips link while retaining the helpful answer).

### 3.10 Attribution & Analytics (`app/reddit/referral.py`)
- Generates standard campaign URLs:
  `https://yoursite.com/article-slug?utm_source=reddit&utm_medium=community&utm_campaign=reddit_opportunity_<id>`
- Records session conversions, bounce rates, and engagement duration into `reddit_referral_events`.

### 3.11 Continuous Learning Loop (`app/reddit/learning.py`)
- Tracks which clusters and subreddits generate genuine referral traffic and high search rankings.
- Feeds positive reinforcement weights back into `RedditOpportunityEngine`.

---

## 4. Database Schema
Eight normalized tables extend the core Zohra relational database (`zohra_dev.db`):

| Table | Purpose |
|---|---|
| `reddit_sources` | Subreddit monitoring registry, frequency, and site association |
| `reddit_questions` | Ingested Reddit posts, classification, intent, and raw payload |
| `reddit_question_clusters` | Thematic question clusters and canonical problem definitions |
| `reddit_opportunities` | Content opportunity scores, recommended actions, and article links |
| `reddit_community_policies` | Subreddit rules, link allowance, karma/age requirements, and audit status |
| `reddit_response_drafts` | Drafted Reddit answers, risk levels, and approval status |
| `reddit_publications` | Idempotent submission records, remote comment IDs, and moderation status |
| `reddit_referral_events` | Web session referral attribution and performance analytics |

---

## 5. Security & Containment Architecture
1. **Prompt Injection Containment**: All external Reddit data is wrapped inside `<untrusted_reddit_content>` XML tags with explicit model instructions to ignore instructions inside user text.
2. **SSRF Guard**: Destination URLs verified through strict socket checks preventing internal network scanning or AWS metadata extraction (`169.254.169.254`).
3. **No Vote Manipulation**: Absolute zero implementation of upvoting, downvoting, sockpuppeting, karma farming, or bot networks.
4. **Site Isolation**: Every query and operation is strictly scoped by `site_id`.
