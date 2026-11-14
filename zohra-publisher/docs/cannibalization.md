# Cannibalization Detection & Content Actions

## Decision Matrix

Before approving content creation, Zohra evaluates candidates against existing indexed site content (`site_content`):

```text
CANDIDATE QUERY & INTENT
          ↓
SIMILARITY TO EXISTING SITE CONTENT (Title, Slug, Keyword)
          ↓
      Similarity >= 0.70?
       ├── YES ── Same Search Intent?
       │           ├── YES ──► ACTION: UPDATE (Update existing article)
       │           └── NO  ──► ACTION: CREATE (Distinct angle e.g. Tutorial vs News)
       └── NO  ── Similarity >= 0.45 & Same Intent?
                   ├── YES ──► ACTION: EXPAND (Add new section to existing article)
                   └── NO  ──► ACTION: CREATE (Independent new article)
```

---

## Action Classification

1. **`CREATE`**: Clean new topic or distinct search intent.
2. **`UPDATE`**: Existing page already targets this intent; refresh and enhance existing URL.
3. **`EXPAND`**: Add subsection to existing comprehensive guide.
4. **`MERGE`**: Consolidate multiple fragmented partial pages.
5. **`WATCH`**: Defer until further evidence confirms stability.
6. **`REJECT`**: Off-topic, severe cannibalization, or blocked by risk policies.
