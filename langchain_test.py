import asyncio
import os
from typing import Optional

import feedparser
import requests
from urllib.parse import quote
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool

from langchain_openai import ChatOpenAI
from semantic_cache import SemanticCache

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Global cache instance - can be set externally (e.g., from Streamlit app)
_cache: Optional[SemanticCache] = None


def set_cache(cache: SemanticCache) -> None:
    """Set the global cache instance."""
    global _cache
    _cache = cache


def get_cache() -> Optional[SemanticCache]:
    """Get the current cache instance."""
    return _cache


def _fetch_google_news(query: str, days: int = 7) -> str:
    """
    Internal function to fetch news from Google News RSS.
    
    Args:
        query: The search topic or keywords.
        days: Number of days to look back for news.
    
    Returns:
        A formatted string with news headlines.
    """
    try:
        # Construct Google News RSS URL
        rss_url = f"https://news.google.com/rss/search?q={quote(query)}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
        
        # Fetch RSS feed with timeout
        response = requests.get(rss_url, timeout=10)
        response.raise_for_status()
        
        # Parse the RSS feed
        feed = feedparser.parse(response.content)
        
        total_articles = len(feed.entries)
        
        if total_articles == 0:
            return f"No news found for '{query}' in the last {days} day(s)."
        
        # Format the results (limit to top 10 for readability)
        max_results = min(10, total_articles)
        headlines = []
        
        for i, item in enumerate(feed.entries[:max_results], 1):
            source = item.source.title if hasattr(item, 'source') and hasattr(item.source, 'title') else "Unknown"
            headlines.append(f"{i}. {item.title}\n   📰 Source: {source}\n   📅 Published: {item.published}")
        
        result = f"Found {total_articles} articles for '{query}' (showing top {max_results}):\n\n"
        result += "\n\n".join(headlines)
        
        return result
        
    except requests.exceptions.Timeout:
        return f"Error: Request timed out while fetching news for '{query}'"
    except requests.exceptions.RequestException as e:
        return f"Error fetching news for '{query}': {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def google_news(query: str, days: int = 7) -> str:
    """
    Fetch the latest news headlines from Google News for a given search query.
    Uses semantic caching to return cached results for similar queries.
    
    Args:
        query: The search topic or keywords (e.g., 'artificial intelligence', 'climate change', 'sports')
        days: Number of days to look back for news (default: 7)
    
    Returns:
        A formatted string with news headlines, sources, and publication dates.
        
    Example: google_news('technology', 3) returns tech news from the last 3 days
    """
    global _cache
    
    # Check cache first if available
    if _cache is not None:
        cached_result = _cache.get_cached_result(query)
        if cached_result is not None:
            result, similarity = cached_result
            return f"[Cache Hit - {similarity:.0%} match]\n\n{result}"
    
    # Fetch fresh results
    result = _fetch_google_news(query, days)
    
    # Store in cache if available and result is not an error
    if _cache is not None and not result.startswith("Error"):
        _cache.store_result(query, result)
    
    return result


async def streaming_multi_step_agent():
    """
    Demonstrates LangChain agent making MULTIPLE tool calls with streaming.
    Watch as the agent thinks, calls tools, and synthesizes results in real-time!
    """
    
    # Initialize model with OpenRouter
    model = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        model="nvidia/nemotron-3-nano-30b-a3b:free",
        temperature=0,
        streaming=True  # Enable streaming
    )
    
    # Define available tools
    tools = [google_news]
    
    print("🤖 Multi-Step Streaming Agent Ready!\n")
    print("Available tools:")
    for t in tools:
        print(f"  • {t.name}: {t.description}")
    
    
        # System prompt to generate Q&A pairs from news headlines
    system_prompt = """You are an expert news analyst and educational content creator. Your task is to use the google news tool to fetch current news headlines and then create high-quality question and answer pairs based on the retrieved content.

**Your Workflow:**
1. Use the google news tool to fetch relevant news headlines based on the user's topic
2. Analyze the headlines, sources, and context
3. Generate 3-5 high-quality Q&A pairs that test understanding of the news

**Q&A Generation Guidelines:**
- Create diverse question types: factual, analytical, inferential, and opinion-based
- Questions should be clear, specific, and directly tied to the news content
- Answers should be comprehensive, accurate, and cite the relevant headline/source when appropriate
- Include a mix of difficulty levels (easy to challenging)
- Focus on key facts, implications, and broader context

**Output Format:**
For each Q&A pair, use this format:

**Q1:** [Question text]
**A1:** [Detailed answer based on news content]

**Q2:** [Question text]
**A2:** [Detailed answer based on news content]

... and so on for 3-5 pairs.

If no relevant news is found or the topic cannot be researched after 3 tool calls, say "I cannot generate Q&A pairs for that topic."
"""
    
    # Create ReAct agent with state_modifier for custom system prompt
    agent = create_agent(model, tools=tools, system_prompt=system_prompt)
    
    while True:
        user_input = input("\n💬 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("\n🧠 Agent working...\n")
        
        try:
            step_number = 0
            tool_call_count = 0
            
            # Stream through agent events using the latest stream_mode="updates" pattern
            # See: https://docs.langchain.com/oss/python/langchain/streaming
            async for chunk in agent.astream(
                {"messages": [{"role": "user", "content": user_input}]},
                stream_mode="updates"
            ):
                for step, data in chunk.items():
                    messages = data.get("messages", [])
                    if not messages:
                        continue
                    
                    last_message = messages[-1]
                    
                    # "model" step: LLM is generating a response (may include tool calls)
                    if step == "model":
                        # Check if the model is requesting tool calls
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                tool_call_count += 1
                                tool_name = tool_call.get("name", "unknown")
                                tool_args = tool_call.get("args", {})
                                
                                print(f"🔧 Tool Call #{tool_call_count}: {tool_name}")
                                
                                # Show what the agent is passing to the tool
                                for key, value in tool_args.items():
                                    print(f"   └─ {key}: {value}")
                        else:
                            # Final answer from the model (no tool calls)
                            # Use content_blocks for standardized access, fallback to content
                            content = (
                                last_message.content_blocks[0].get("text", "")
                                if hasattr(last_message, "content_blocks") and last_message.content_blocks
                                else last_message.content
                            )
                            if content:
                                print(f"💡 Agent's Reasoning & Answer:")
                                print(f"   {content}")
                                print(f"\n📊 Summary: Used {tool_call_count} tool call(s) across {step_number} step(s)")
                    
                    # "tools" step: Tool execution completed
                    elif step == "tools":
                        step_number += 1
                        # Use content_blocks for standardized access, fallback to content
                        tool_output = (
                            last_message.content_blocks[0].get("text", "")
                            if hasattr(last_message, "content_blocks") and last_message.content_blocks
                            else last_message.content
                        )
                        print(f"\n✅ Step {step_number} Complete: {last_message.name}")
                        print(f"   └─ Output: {tool_output}")
                        print()
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    print("\n⚠️  Set OPENROUTER_API_KEY before running!")
    print("Get your key at: https://openrouter.ai/keys\n")
    asyncio.run(streaming_multi_step_agent())