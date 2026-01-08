from gdeltdoc import GdeltDoc, Filters
import pandas as pd
from llm_service import get_llm
from gdeltdoc import Filters, near, repeat, multi_repeat

query = "nvidia"
f = Filters(
    keyword = query,
    start_date = "2025-01-01",
    end_date = "2025-01-07",
    # language="eng",
    num_records=200,
    # near=near(10, "nvidia", "CES"),
    # repeat = multi_repeat([(2, "gpu"), (2, "rubin")], "AND")
)

gd = GdeltDoc()

# Search for articles matching the filters
articles = gd.article_search(f)

print(articles.columns)
print(articles.head())
print(articles.shape)

file_name  = query.replace(" ", "_")
articles.to_csv(f"{file_name}.csv", index=False)


llm_service = get_llm()

prompt = f"""
You are a news analyst extracting insights from headlines.

INPUT: Collection of news headlines (possibly in multiple languages)
{articles['title'].to_string()}

TASK:
1. Identify main topics and themes across headlines
2. Note significant events, trends, or patterns
3. Work ONLY with what's explicitly stated - no speculation

OUTPUT: Single markdown document with the following sections:

# News Insights Summary

## Key Topics & Themes
List the 3-5 main topics with brief context and example headlines that demonstrate each theme.

## Notable Events
Bullet points of specific events clearly mentioned in headlines.

## Emerging Patterns
Any trends or patterns visible across multiple headlines.

## Limitations
Note any headlines that were unclear or lacked sufficient context.

FORMATTING RULES:
- Use paragraphs, lists, and bullet points only
- NO tables, NO numbered sections beyond headers
- Keep it concise and scannable
- Focus on what's observable, not what's inferred
"""

response = llm_service.invoke(prompt)
print(response.content)