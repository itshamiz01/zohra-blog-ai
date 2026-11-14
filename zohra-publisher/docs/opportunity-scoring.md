# Opportunity Scoring Formula & Weight Profiles

## Positive Scoring Weights

| Component | Default | Breaking News | Evergreen | Commercial Comparison |
|---|---|---|---|---|
| Search Demand | 15% | 15% | 20% | 15% |
| Search Intent Strength | 10% | 10% | 10% | 15% |
| Competition Opportunity | 10% | 10% | 10% | 15% |
| Site Relevance | 12% | 15% | 15% | 10% |
| Topical Authority | 8% | 5% | 15% | 5% |
| Trend Strength | 10% | 20% | 5% | 5% |
| Freshness | 8% | 20% | 3% | 5% |
| Evergreen Potential | 7% | 2% | 20% | 5% |
| Original Value Potential | 8% | 10% | 10% | 10% |
| SERP Gap | 5% | 5% | 5% | 5% |
| Monetization Potential | 5% | 2% | 5% | 20% |
| Audience Fit | 2% | 2% | 2% | 2% |
| **Total** | **100%** | **100%** | **100%** | **100%** |

---

## Penalty Deductions

- **Cannibalization Penalty**: Deducts up to $25.0$ points if attempting `CREATE` when risk $> 50$.
- **Risk Policy Penalty**: Deducts up to $30.0$ points for unverified YMYL/medical/legal claims.
- **Extreme Competition Penalty**: Deducts $18.0$ points if official portal totally monopolizes SERP.
- **Expiration Penalty**: Deducts $40.0$ points if the temporal window has already passed.

$$\text{Final Opportunity Score} = \max(0.0, \min(100.0, \text{Positive Score} - \text{Total Penalties}))$$
