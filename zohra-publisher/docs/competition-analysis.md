# Competition Analysis & Zohra Competition Score

## Zohra Competition Score Formula

Zohra never outputs third-party proprietary "Keyword Difficulty" numbers unless provided by an authentic API.
Instead, it calculates the transparent **Zohra Competition Score** (0 to 100):

$$\text{Zohra Competition Score} = \text{Base} (40) + \text{OfficialDomainBonus} (25) + \text{HighAuthDominance} (0\dots 25) - \text{ForumDiscount} (0\dots 15) + \text{ExactMatchSaturation} (0\dots 15)$$

- Normalized strictly between $10.0$ and $98.0$.
- **Competition Opportunity Score** = $100.0 - \text{Competition Score}$. Higher means easier opportunity to capture ranking share.

---

## Domain Dominance & Competitor Tracking

Top 5 ranking domains are evaluated for:
- Apparent specialization (official documentation, broad tech media, niche blogs, community forums)
- Brand dominance: presence of Wikipedia, TechCrunch, The Verge, Forbes, etc.
- Freshness: average publication age of ranking URLs.
