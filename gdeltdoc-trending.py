from gdeltdoc import GdeltDoc, Filters
import pandas as pd

# def fetch_trending_news(theme, country="IN", timespan="24h", limit=50):
#     """
#     Pulls trending news articles based on a specific GDELT theme.
#     """
#     gd = GdeltDoc()
    
#     # Define Filters
#     # Themes: Use GKG themes like 'TAX_FNCACT_SEMICONDUCTORS', 'ECON_REFORM', etc.
#     f = Filters(
#         theme = theme,
#         country = country,
#         timespan = timespan,
#         num_records = limit
#     )

#     # Search for articles
#     articles = gd.article_search(f)
    
#     if articles.empty:
#         print(f"No articles found for theme: {theme}")
#         return None
    
#     # Sort by 'seendate' (most recent first)
#     articles = articles.sort_values(by="seendate", ascending=False)
    
#     return articles

# # --- Example Usage ---
# # Themes follow GKG taxonomy. General examples: 
# # 'WB_ECONOMY', 'GENERAL_HEALTH', 'UNGP_INFRASTRUCTURE'
# target_theme = "EDUCATION" 

# df_news = fetch_trending_news(theme=target_theme, country="IN")

# if df_news is not None:
#     print(f"Successfully pulled {len(df_news)} articles for {target_theme}")
#     # Display top 5 results
#     print(df_news[['title', 'url', 'sourcecountry']].head())
    
#     # Save to CSV for your indexer
#     # df_news.to_csv("daily_news_index.csv", index=False)

####################################################################################

# import requests

# def get_top_themes_by_country(country_code="IN", timespan="24h"):
#     # The 'summary' API mode=topthemes gives you the most frequent themes
#     url = "https://api.gdeltproject.org/api/v2/summary/summary"
#     params = {
#         "dataset": "gkg",
#         "query": f"location:{country_code}",
#         "timespan": timespan,
#         "mode": "topthemes",
#         "format": "json"
#     }
    
#     response = requests.get(url, params=params)

#     print(response.text)
    
#     if response.status_code == 200:
#         data = response.json()
#         # The API returns a list of themes and their frequency
#         return data.get("topthemes", [])
#     else:
#         print(f"Error: {response.status_code}")
#         return []

# # Fetch top themes for India in the last 24 hours
# themes = get_top_themes_by_country("IN")
# for t in themes[:10]:
#   print(f"Theme: {t['label']} | Frequency: {t['count']}")

####################################################################################
import time
import requests
import re
import json
from gdeltdoc import GdeltDoc, Filters

def get_trending_keywords(country_code="IN"):
    """
    Step 1: Scrape the Trending Word Cloud dashboard.
    Extracts keywords from the JavaScript data embedded in the HTML.
    """
    print(f"--- Fetching trending topics for {country_code} ---")
    url = f"https://api.gdeltproject.org/api/v1/dash_thematicwordcloud/dash_thematicwordcloud?LOC={country_code}&VAR=trendall"
    
    try:
        response = requests.get(url)
        html_content = response.text
        
        # Find the JavaScript array containing the keywords
        # Pattern: .words( [ {text: 'keyword', size: number}, ... ] )
        pattern = r'\.words\(\s*\[\s*(.*?)\s*\]\s*\)'
        match = re.search(pattern, html_content, re.DOTALL)
        
        if not match:
            print("Could not find keywords in the response.")
            return []
        
        # Extract the array content
        array_content = match.group(1)
        
        # Parse individual keyword objects using regex
        # Pattern: {text: 'keyword', size: number}
        keyword_pattern = r'\{text:\s*["\']([^"\']+)["\'],\s*size:\s*\d+\}'
        keywords_raw = re.findall(keyword_pattern, array_content)
        
        # Clean and filter keywords
        keywords = [k.strip() for k in keywords_raw if len(k.strip()) > 2]
        
        # Remove duplicates while preserving order
        unique_keywords = list(dict.fromkeys(keywords))
        
        print(f"Found {len(unique_keywords)} unique keywords.")
        return unique_keywords
        
    except Exception as e:
        print(f"Error scraping trends: {e}")
        return []

def main():
    # 1. Initialize the GDELT Doc client
    gd = GdeltDoc()
    
    # 2. Get keywords from the visual dashboard
    trending_words = get_trending_keywords("IN")
    
    if not trending_words:
        print("No keywords found.")
        return

    # 3. Iterate using gdeltdoc
    # Limiting to top 5 to respect rate limits
    for word in trending_words[:5]:
        print(f"\nProcessing Topic: {word}")
        
        # Step 2: Set up Filters using the gdeltdoc package
        f = Filters(
            keyword = word,
            start_date = "2026-01-01", # GDELT uses YYYY-MM-DD
            end_date = "2026-01-08",
            country = "IN"             # Filters by source country
        )

        # Execute Search
        # mode="artlist" returns a Pandas DataFrame by default in this package
        try:
            articles = gd.article_search(f)
            
            if not articles.empty:
                # Display top 3 results from the DataFrame
                for index, row in articles.head(3).iterrows():
                    print(f" - {row['title']}")
                    print(f"   Link: {row['url']}")
            else:
                print("   No articles found for this keyword.")
                
        except Exception as e:
            print(f"   Error fetching data for {word}: {e}")

        # GDELT requires a delay between API calls
        time.sleep(5)

if __name__ == "__main__":
    main()