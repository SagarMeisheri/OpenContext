# GDELT Python API Search Guide

Quick reference for optimizing GDELT searches using `gdeltdoc` library.

---

## Basic Template

```python
from gdeltdoc import GdeltDoc, Filters, near, repeat, multi_near, multi_repeat

f = Filters(
    keyword = "your search terms",
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 50
)

gd = GdeltDoc()
articles = gd.article_search(f)
```

---

## Filter Parameters

### 1. `keyword` - What to search for
```python
keyword = "donald trump"              # Simple phrase
keyword = "climate change policy"     # Multiple words
```
**Rule:** Keep it simple. 1-3 words max.

### 2. `near` - Words appearing close together
```python
near = near(15, "trump", "chicago")   # Within 15 words
```
**Distance guide:**
- `5-10` = Very tight (same sentence)
- `15-20` = Moderate (nearby sentences) ⭐ **RECOMMENDED**
- `25-50` = Loose (same article)

### 3. `repeat` - Word appears multiple times
```python
repeat = repeat(2, "chicago")         # "chicago" appears 2+ times
```
**Count guide:**
- `2` = Mentioned/discussed ⭐ **RECOMMENDED**
- `3` = Significant topic
- `4+` = Main focus (very restrictive)

### 4. Date Range
```python
start_date = "2025-01-01"             # YYYY-MM-DD
end_date = "2025-01-07"
```

### 5. Language & Records
```python
language = "eng"                      # eng, spa, fra, deu, etc.
num_records = 50                      # Max: 250
```

---

## Common Search Patterns

### Person + Location
```python
# "Donald Trump and Chicago"
Filters(
    keyword = "trump chicago",
    near = near(15, "trump", "chicago"),
    repeat = repeat(2, "chicago"),
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng"
)
```

### Company + Event
```python
# "Tesla recall news"
Filters(
    keyword = "tesla",
    near = near(10, "tesla", "recall"),
    repeat = repeat(2, "recall")
)
```

### Topic + Country
```python
# "Air pollution in Delhi"
Filters(
    keyword = "air pollution delhi",
    near = near(20, "pollution", "delhi"),
    repeat = repeat(2, "delhi"),
    country = "IN"
)
```

### Multiple Relationships (OR)
```python
# "Airline and climate OR crisis"
Filters(
    keyword = "airline",
    near = multi_near([
        (10, "airline", "climate"),
        (10, "airline", "crisis")
    ], method="OR")
)
```

### Multiple Relationships (AND)
```python
# "Airline mentions climate AND crisis"
Filters(
    keyword = "airline",
    near = multi_near([
        (15, "airline", "climate"),
        (15, "airline", "crisis")
    ], method="AND")
)
```

---

## Search Strategies

### Strategy 1: First Search (Broad)
```python
Filters(
    keyword = "your topic",
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 100
)
# No near or repeat - see what you get first
```

### Strategy 2: Focused Search (Recommended)
```python
Filters(
    keyword = "your topic",
    near = near(15, "word1", "word2"),     # Add context
    repeat = repeat(2, "important_word"),  # Ensure relevance
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 50
)
```

### Strategy 3: Precise Search (Few results)
```python
Filters(
    keyword = "specific phrase",
    near = near(10, "word1", "word2"),
    repeat = multi_repeat([
        (2, "word1"),
        (2, "word2")
    ], method="AND"),
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    num_records = 25
)
```

---

## Quick Optimization Rules

### ✅ Do This
- Start with just `keyword`, then add filters
- Use `near(15, ...)` as default distance
- Use `repeat(2, ...)` to ensure topic relevance
- Keep `keyword` simple (1-3 words)
- Test and adjust based on results

### ❌ Avoid This
- `repeat(3+, ...)` - Too restrictive
- `near(5, ...)` - Too tight unless very specific
- Too many words in `keyword`
- `multi_repeat(..., "AND")` - Use sparingly

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Too few results** | Remove `repeat`, increase `near` distance, simplify `keyword` |
| **Too many irrelevant results** | Add `repeat(2, ...)`, reduce `near` distance, add more specific keyword |
| **Not sure what to use** | Start with just `keyword` + dates, review results, then add filters |

---

## Complete Examples

### Example 1: Trump + Chicago
```python
f = Filters(
    keyword = "trump",
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 50,
    near = near(15, "trump", "chicago"),
    repeat = repeat(2, "chicago")
)
```

### Example 2: Venezuela Crisis
```python
f = Filters(
    keyword = "venezuela",
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 50,
    near = near(15, "maduro", "election"),
    repeat = repeat(2, "venezuela")
)
```

### Example 3: Company Acquisition
```python
f = Filters(
    keyword = "nvidia groq",
    start_date = "2024-12-01",
    end_date = "2025-01-07",
    language = "eng",
    num_records = 30,
    near = near(10, "nvidia", "groq")
)
```

---

## Pro Tips

1. **Start simple** - Just use `keyword` first
2. **Use near(15)** - Best balance for most searches
3. **Use repeat(2)** - Ensures relevance without over-filtering
4. **Short date ranges** - 7-14 days for events, 30+ for trends
5. **Save results** - Use `.to_csv()` to cache data
6. **Iterate** - Review results → adjust filters → search again

---

## Quick Reference

| Filter | Default Value | Use When |
|--------|--------------|----------|
| `keyword` | 1-3 words | Always |
| `near()` | 15 words | Need related concepts |
| `repeat()` | 2 times | Too many tangential results |
| `start_date/end_date` | 7-14 days | Always |
| `language` | "eng" | English content |
| `num_records` | 50 | Always |

---

**Remember:** Simple is better. Start basic → test → refine.

