# Brand Voice, Stylistic Transformation & Factual Invariance
## Zohra Editorial Intelligence System

### 1. Architectural Principle
Brand voice controls how ideas are communicated (rhythm, formality, vocabulary level, sentence style, humor, directness).
It must **never** alter factual meaning.

$$\mathbf{FACTUAL\ INVARIANCE\ INVARIANT}$$

Every number, currency symbol, date, quote, and core factual claim extracted before brand transformation must exactly match the post-transformation content. If stylistic rewriting modifies, rounds, or removes any numeric or temporal token:
1. The transformation is flagged as invalid.
2. The transformation is rolled back to the pre-transformed text.

---

### 2. Multi-Language Native Writing
Rather than writing English content and applying crude machine translation, Zohra generates native-language drafts (English, Hindi, Spanish) directly from the underlying evidence package.
Factual consistency tests (`MultilingualEngine.verify_multilingual_consistency`) verify that identical numbers, dates, and claims persist across all localized editions.
