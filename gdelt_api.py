"""
GDELT API Query Agent using LangChain.

This script uses a LangChain agent with LLM to:
1. Formulate proper GDELT API queries from natural language
2. Execute the queries against GDELT API
3. Return structured results
"""

import asyncio
import json
import requests
from typing import Dict, Any
from langchain.tools import tool
from langchain.agents import create_agent

from llm_service import get_llm


# --- GDELT API TOOL ---
@tool
def execute_gdelt_query(
    query_string: str, 
    mode: str = "artlist", 
    timespan: str = "1w",
    max_records: int = 50
) -> str:
    """
    Executes a GDELT API query and returns results.
    
    Args:
        query_string: Formatted GDELT query string
        mode: API mode - 'artlist' (articles), 'timelinevol' (trends), 'wordcloudnative' (keywords)
        timespan: Time range - '24h', '1w' (1 week), '1m' (1 month), '3m' (3 months)
        max_records: Maximum number of results to return (default: 10)
    
    Returns:
        JSON string with query results or error message
    """
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query_string,
        "mode": mode,
        "timespan": timespan,
        "format": "json",
        "maxrecords": max_records
    }
    
    try:
        print("\n" + "="*80)
        print("🔧 AGENT TOOL CALL: execute_gdelt_query")
        print("="*80)
        print(f"🔍 Executing GDELT query: {query_string}")
        print(f"   Mode: {mode}, Timespan: {timespan}, Max Records: {max_records}")
        print(f"   Sending request to GDELT API...")
        
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        print(f"   ✅ API response received (Status: {response.status_code})")
        
        data = response.json()
        
        # Format the response for better readability
        print(f"   📊 Formatting response data...")
        if mode == "artlist" and "articles" in data:
            articles = data["articles"][:max_records]
            result = {
                "success": True,
                "count": len(articles),
                "articles": [
                    {
                        "title": art.get("title", "No title"),
                        "url": art.get("url", ""),
                        "source": art.get("domain", "Unknown"),
                        "date": art.get("seendate", ""),
                        "language": art.get("language", "")
                    }
                    for art in articles
                ]
            }
            print(f"   ✅ Formatted {len(articles)} articles")
        else:
            result = {"success": True, "data": data}
            print(f"   ✅ Data formatted successfully")
        
        print("   🎁 Returning results to agent...")
        print("="*80)
        return json.dumps(result, indent=2)
        
    except requests.exceptions.RequestException as e:
        error_result = {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "query": query_string
        }
        return json.dumps(error_result, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "query": query_string
        }
        return json.dumps(error_result, indent=2)


# --- AGENT SETUP ---
GDELT_AGENT_SYSTEM_PROMPT = """You are a GDELT API query expert. Your job is to help users search for news articles using the GDELT database.

When a user provides a search query, you MUST:
1. Analyze the user's query to understand their intent
2. Use the 'execute_gdelt_query' tool to search the GDELT database with a properly formatted query
3. **ALWAYS summarize the results returned from the tool in a clear and comprehensive manner**

GDELT Query Formulation Guidelines:
- Use quotes for exact phrases: "nvidia" "groq" "acquisition"
- Use 'near10:' or 'near20:' for words that should appear close together: near10:"nvidia groq"
- For geographic filtering: add sourcecountry:XX (e.g., sourcecountry:US)
- For ensuring relevance: use repeat2 or repeat3 for key terms: repeat3:"nvidia"
- Combine terms logically with AND, OR, or proximity operators
- Use parentheses for grouping: (nvidia OR groq) acquisition

Examples:
- "nvidia buys groq" → near10:"nvidia groq" (acquisition OR buyout OR purchase)
- "scams in India" → "scam" sourcecountry:IN
- "AI partnerships" → near20:"AI partnership"

**After receiving results from the tool, you MUST provide a summary that includes:**
- Number of articles found
- Key themes and topics from the articles
- Notable sources
- Brief overview of what the articles are about
- DO NOT just return the raw JSON - provide an analytical summary"""


def create_gdelt_agent():
    """
    Creates a LangChain agent for GDELT API queries using the new API.
    
    Returns:
        Configured agent that can be invoked with messages
    """
    print("   🔧 Loading LLM with temperature=0.1 for precise queries...")
    llm = get_llm(temperature=0.1)  # Low temperature for precise query formulation
    
    print("   🛠️  Registering GDELT query tool...")
    tools = [execute_gdelt_query]
    
    print("   📝 Applying system prompt with GDELT query guidelines...")
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=GDELT_AGENT_SYSTEM_PROMPT
    )
    
    return agent


async def search_gdelt(query: str) -> Dict[str, Any]:
    """
    Search GDELT using natural language query via LangChain agent.
    
    Args:
        query: Natural language search query
        
    Returns:
        Dictionary with search results
    """
    try:
        print("\n" + "="*80)
        print("🚀 STEP 1: Initializing GDELT Agent")
        print("="*80)
        agent = create_gdelt_agent()
        print("✅ Agent created successfully")
        
        print("\n" + "="*80)
        print("🤔 STEP 2: Agent analyzing user query")
        print(f"   Query: '{query}'")
        print("="*80)
        
        # Use the new messages-based API
        print("\n📤 STEP 3: Sending query to agent...")
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": f"Search GDELT for: {query}"}]
        })
        print("✅ Agent invocation completed")
        
        print("\n" + "="*80)
        print("📥 STEP 4: Agent generating summary of results")
        print("="*80)
        
        # Extract the final response from messages
        messages = result.get("messages", [])
        print(f"   Received {len(messages)} messages from agent")
        
        final_answer = ""
        if messages:
            print("   Extracting agent's final summary...")
            # Get the last AI message (which should be the summary)
            for i, msg in enumerate(reversed(messages)):
                # Check if it's an AI message with content
                if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'content') and msg.content:
                    final_answer = msg.content
                    print(f"   ✅ Found agent summary in message {len(messages) - i}")
                    break
                elif hasattr(msg, 'content') and msg.content and 'tool' not in str(type(msg)).lower():
                    # Fallback: get any message with content that's not a tool message
                    final_answer = msg.content
                    print(f"   ✅ Found response in message {len(messages) - i}")
                    break
        
        print("\n" + "="*80)
        print("🎉 STEP 5: Returning results to user")
        print("="*80)
        
        if final_answer:
            print(f"   📝 Summary length: {len(final_answer)} characters")
        else:
            print("   ⚠️  Warning: No summary generated by agent")
        
        return {
            "success": True,
            "query": query,
            "result": final_answer or "No summary generated",
            "raw": result
        }
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR: Agent execution failed")
        print("="*80)
        print(f"   Error: {str(e)}")
        return {
            "success": False,
            "query": query,
            "error": str(e)
        }


# --- TEST FUNCTIONS ---
async def test_sample_query(query: str):
    """
    Test the agent with the query
    """
    print("=" * 80)
    print(f"🧪 Testing GDELT Agent with Query: '{query}'")
    print("=" * 80)
    
    result = await search_gdelt(query)
    
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    
    if result["success"]:
        print(f"\n✅ Query: {result['query']}")
        print(f"\n📄 Agent Summary:\n")
        print(result['result'])
    else:
        print(f"\n❌ Query failed: {result['query']}")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result


async def test_multiple_queries():
    """
    Test the agent with multiple different queries.
    """
    test_queries = [
        "nvidia buys groq ai startup",
        "AI regulation in Europe",
        "cryptocurrency fraud in India",
        "climate change policies USA"
    ]
    
    results = []
    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"🔍 Testing Query: {query}")
        print("=" * 80)
        
        result = await search_gdelt(query)
        results.append(result)
        
        # Brief pause between queries
        await asyncio.sleep(1)
    
    return results


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Test the nvidia/groq query

    input_query = input("Enter a query: ")
    asyncio.run(test_sample_query(query=input_query))