import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_added_text(page_title, days=30, limit=500):
    # 1. Get the list of recent revisions for the page
    url = "https://en.wikipedia.org/w/api.php"
    
    # Wikipedia requires a User-Agent header
    headers = {
        'User-Agent': 'WikiEditAnalyzer/1.0 (Python script for analyzing Wikipedia edits)'
    }
    
    # Calculate the date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Format dates as ISO 8601 (Wikipedia API format)
    rvstart = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    rvend = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "ids|timestamp|user|comment|parentid",
        "rvlimit": limit,  # Max revisions to fetch (API max is 500)
        "rvstart": rvstart,  # Start from most recent
        "rvend": rvend,      # Go back to this date
        "rvslots": "main"
    }

    try:
        print(f"Fetching revisions for: {page_title}")
        print(f"Date range: Last {days} days (from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        print(f"Request URL: {url}")
        print(f"Request params: {params}\n")
        
        resp = requests.get(url, params=params, headers=headers)
        print(f"Initial response status: {resp.status_code}")
        
        try:
            response = resp.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Error: Initial API request failed. Response: {resp.text[:200]}")
            return
        
        pages = response["query"]["pages"]
        page_id = next(iter(pages))
        revisions = pages[page_id].get("revisions", [])
        print(f"Found {len(revisions)} revisions\n")
        
        print(f"Analyzing {len(revisions)} edits for '{page_title}' in the last {days} days\n" + "="*50)

        for i, rev in enumerate(revisions):
            rev_id = rev['revid']
            parent_id = rev.get('parentid')
            user = rev.get('user', 'Hidden')
            timestamp = rev['timestamp']
            
            # Skip if there's no parent revision (first revision of the page)
            if not parent_id:
                print(f"\n[Edit ID: {rev_id}] (Initial page creation)")
                continue
            
            # 2. For each revision, ask the API for the "Compare" (Diff) data
            # This compares the current revision (rev_id) with its parent revision
            print(f"\n--- Processing revision {i+1}/{len(revisions)} ---")
            print(f"Rev ID: {rev_id}, Parent ID: {parent_id}, User: {user}")
            
            compare_params = {
                "action": "compare",
                "format": "json",
                "fromrev": parent_id,  # Older revision
                "torev": rev_id  # Newer revision
            }
            
            print(f"Comparison params: {compare_params}")
            compare_resp = requests.get(url, params=compare_params, headers=headers)
            print(f"Compare response status: {compare_resp.status_code}")
            
            try:
                compare_response = compare_resp.json()
                print(f"Compare response keys: {compare_response.keys()}")
            except requests.exceptions.JSONDecodeError:
                print(f"Error: API returned non-JSON response")
                print(f"Response text: {compare_resp.text[:300]}")
                continue
            
            added_lines = []
            
            # 3. Parse the HTML Diff to find added text
            # The API returns an HTML table. Added text is usually in <td class="diff-addedline">
            if "compare" in compare_response and "*" in compare_response["compare"]:
                diff_html = compare_response["compare"]["*"]
                print(f"Diff HTML length: {len(diff_html)} characters")
                soup = BeautifulSoup(diff_html, "html.parser")
                
                # Wikipedia marks added lines with the class 'diff-addedline'
                # Inside that, the specific added text is often in <ins> tags or just raw text
                added_chunks = soup.find_all("td", class_="diff-addedline")
                print(f"Found {len(added_chunks)} added chunks")
                
                for chunk in added_chunks:
                    text = chunk.get_text().strip()
                    if text:
                        added_lines.append(text)
            else:
                print("No compare data in response")

            # Output the results for this revision
            if added_lines:
                print(f"\n✅ [Edit ID: {rev_id}] by {user} on {timestamp}")
                print(f"Comment: {rev.get('comment', 'No comment')}")
                print("-" * 20)
                print("ADDED TEXT:")
                for line in added_lines:
                    print(f"+ {line}")
            else:
                print(f"ℹ️  [Edit ID: {rev_id}] (No text additions detected / Formatting change only)")
            
            print("="*50)

    except Exception as e:
        print(f"Error: {e}")

# --- RUN THE SCRIPT ---
# Example: Get all edits for "Groq" page in the last 30 days
# You can adjust the days parameter (e.g., days=7 for last week, days=90 for last 3 months)
get_added_text("Groq", days=30)