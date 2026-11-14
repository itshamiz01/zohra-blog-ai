# Search Intent Classification & Specificity Strength

## The 10 Canonical Search Intents

Zohra classifies search queries into 10 explicit intent categories:

| Intent | Definition | Example Query |
|---|---|---|
| `informational` | General understanding or conceptual knowledge | `what is transformer architecture` |
| `navigational` | Seeking a specific official portal, login, or destination | `chatgpt login`, `runway official site` |
| `commercial_investigation` | Evaluating pricing, tiers, features before buying | `claude pro pricing`, `is runway worth it` |
| `transactional` | Direct intent to purchase, subscribe, or download | `buy github copilot license`, `download whisper` |
| `news` | Temporal announcements, launch updates, breaking changes | `openai announces model x today` |
| `comparison` | Head-to-head benchmarking between two or more solutions | `model x vs runway gen-3` |
| `tutorial` | Step-by-step practical guide or implementation walkthrough | `how to use model x for youtube videos` |
| `troubleshooting` | Diagnosing errors, bug fixes, or failure states | `model x api timeout error fix` |
| `local` | Geographic destination or local service | `ai meetup bangalore` |
| `reference` | API specifications, syntax, cheatsheets, limitations | `model x api rate limits documentation` |

---

## Intent Specificity Strength

Queries are scored from 0 to 100 for specificity (`intent_strength_score`):
- `AI` $\rightarrow$ 25 (vague, high ambiguity)
- `AI video generators` $\rightarrow$ 50 (broad commercial category)
- `How to use Runway for YouTube Shorts automation` $\rightarrow$ 94 (actionable, precise intent, high conversion value)

Highly specific queries receive higher utility scores even when raw search volume is lower.
