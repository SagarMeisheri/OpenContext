"""
GDELT Full Text Search - Multi-Query Decomposition Tool
Breaks down complex queries into multiple sub-queries and aggregates results
Uses GDELT FTS API (last 24 hours across 65 languages)
"""

import requests
from typing import List, Dict, Any, Optional
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor, as_completed
import json


# ============================================================================
# CONFIGURATION
# ============================================================================

GDELT_FTS_URL = "https://api.gdeltproject.org/api/v1/search_ftxtsearch/search_ftxtsearch"


# ============================================================================
# MULTI-QUERY TOOL INPUT SCHEMA
# ============================================================================

class MultiQueryFTSInput(BaseModel):
    """Input for multi-query full text search"""
    query: str = Field(description="Complex query to decompose and search")
    num_subqueries: int = Field(default=5, description="Number of sub-queries to generate (3-10)")
    hours: int = Field(default=24, description="Hours to search back (max 24)")
    aggregate_strategy: str = Field(
        default="comprehensive",
        description="'comprehensive' (all results), 'top' (best from each), or 'diverse' (unique angles)"
    )


# ============================================================================
# QUERY DECOMPOSER
# ============================================================================

class FTSQueryDecomposer:
    """Decomposes complex queries into multiple specific sub-queries"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(temperature=0.3, model="gpt-4")
    
    def decompose(self, query: str, num_queries: int = 5) -> List[str]:
        """
        Decompose a complex query into multiple specific sub-queries
        Optimized for GDELT Full Text Search (24-hour window)
        """
        prompt = f"""You are an expert at breaking down complex news search queries into multiple specific sub-queries.

Original query: "{query}"

Generate {num_queries} specific sub-queries that:
1. Cover different aspects of the topic
2. Use specific keywords/phrases that would appear in news articles
3. Are optimized for searching last 24 hours of news
4. Focus on recent developments and breaking news angles
5. Don't overlap too much
6. Together provide comprehensive coverage

Guidelines:
- Use quoted phrases for exact matches: "climate change"
- Include breaking news keywords: "latest", "breaking", "update"
- Think about what journalists would write in headlines
- Consider different angles (economic, political, social, regional)

Return ONLY a JSON array of sub-queries, nothing else.
Example format: ["sub-query 1", "sub-query 2", ...]

Sub-queries:"""

        response = self.llm.invoke(prompt)
        
        try:
            # Extract JSON from response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            subqueries = json.loads(content)
            
            if not isinstance(subqueries, list):
                subqueries = [str(subqueries)]
            
            return subqueries[:num_queries]
            
        except Exception as e:
            print(f"Error decomposing query: {e}")
            # Fallback: create variations
            return [
                query,
                f'"{query}" latest',
                f"{query} breaking news",
                f"{query} update",
                f"{query} development"
            ][:num_queries]


# ============================================================================
# RESULT AGGREGATOR
# ============================================================================

class FTSResultAggregator:
    """Aggregates and synthesizes results from multiple FTS queries"""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(temperature=0.2, model="gpt-4")
    
    def aggregate(
        self,
        original_query: str,
        subquery_results: List[Dict[str, Any]],
        strategy: str = "comprehensive"
    ) -> str:
        """Aggregate results from multiple sub-queries"""
        
        # Collect all articles
        all_articles = []
        for result in subquery_results:
            all_articles.extend(result.get("articles", []))
        
        # Remove duplicates by URL
        unique_articles = {}
        for article in all_articles:
            url = article.get("url", "")
            if url and url not in unique_articles:
                unique_articles[url] = article
        
        articles = list(unique_articles.values())
        
        # Apply strategy
        if strategy == "top":
            articles = articles[:20]
        elif strategy == "diverse":
            # Take top 3 from each sub-query
            articles = []
            for result in subquery_results:
                articles.extend(result.get("articles", [])[:3])
        
        if not articles:
            return f"No articles found for: {original_query}"
        
        # Create synthesis prompt
        articles_text = "\n\n".join([
            f"URL: {a['url']}\nDate: {a.get('date', 'Unknown')}\nLanguage: {a.get('lang', 'Unknown')}"
            for a in articles[:30]  # Limit to 30 for context
        ])
        
        subqueries_text = "\n".join([
            f"- {r['subquery']} ({len(r.get('articles', []))} results)"
            for r in subquery_results
        ])
        
        prompt = f"""You are a news analyst synthesizing information from multiple search queries.

Original Question: "{original_query}"

Sub-queries executed:
{subqueries_text}

Articles found (top {min(len(articles), 30)} of {len(articles)} total):
{articles_text}

Provide a comprehensive answer that:
1. Directly answers the original question
2. Synthesizes insights from all sub-queries
3. Identifies key themes and patterns
4. Notes important dates and sources
5. Highlights breaking/recent developments
6. Is well-structured with clear sections

Your comprehensive analysis:"""

        response = self.llm.invoke(prompt)
        
        # Add metadata
        summary = response.content
        summary += f"\n\n---\n**Search Coverage:**\n"
        summary += f"- Total unique articles: {len(articles)}\n"
        summary += f"- Sub-queries executed: {len(subquery_results)}\n"
        summary += f"- Time range: Last 24 hours\n"
        summary += f"- Languages covered: {len(set(a.get('lang', '') for a in articles))} languages\n"
        
        return summary


# ============================================================================
# FTS API CALLER
# ============================================================================

def call_fts_api(query: str, hours: int = 24, max_results: int = 50) -> Dict[str, Any]:
    """
    Call GDELT Full Text Search API
    
    Args:
        query: Search query
        hours: Hours to search back (max 24)
        max_results: Max articles to return
    
    Returns:
        API response with articles
    """
    # Convert hours to minutes (round to 15-min increments)
    minutes = min(hours * 60, 1440)
    if minutes < 1440:
        query = f"{query} lastminutes:{minutes}"
    
    params = {
        "query": query,
        "output": "urllist",
        "maxrows": max_results,
        "dropdup": "true"
    }
    
    try:
        response = requests.get(GDELT_FTS_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse CSV response
        lines = response.text.strip().split('\n')
        articles = []
        
        for line in lines[1:]:  # Skip header
            parts = line.split(',', 2)  # Split into 3 parts max
            if len(parts) >= 3:
                articles.append({
                    "date": parts[0],
                    "lang": parts[1],
                    "url": parts[2]
                })
        
        return {
            "subquery": query,
            "articles": articles,
            "success": True
        }
        
    except Exception as e:
        return {
            "subquery": query,
            "articles": [],
            "success": False,
            "error": str(e)
        }


# ============================================================================
# MULTI-QUERY SEARCH TOOL
# ============================================================================

class GDELTMultiQueryFTSTool(BaseTool):
    """
    Multi-query full text search tool
    Decomposes complex queries and aggregates results
    """
    name: str = "multi_query_fts_search"
    description: str = """Use this for complex, multi-faceted news searches requiring comprehensive coverage.
    Automatically breaks down your query into 5-10 specific sub-queries, searches each in parallel,
    and synthesizes all results into a comprehensive answer.
    
    Searches last 24 hours across 65 languages with real-time translation.
    
    Best for:
    - Broad topics needing multiple angles
    - Comparative analyses
    - Comprehensive reports
    - Complex questions requiring diverse sources
    - Breaking news with multiple aspects
    
    Returns synthesized summary with insights from all sub-queries."""
    
    args_schema: type[BaseModel] = MultiQueryFTSInput
    
    def __init__(self):
        super().__init__()
        self.decomposer = FTSQueryDecomposer()
        self.aggregator = FTSResultAggregator()
    
    def _run(
        self,
        query: str,
        num_subqueries: int = 5,
        hours: int = 24,
        aggregate_strategy: str = "comprehensive"
    ) -> str:
        """Execute multi-query FTS search"""
        
        # Validate inputs
        num_subqueries = max(3, min(10, num_subqueries))
        hours = min(hours, 24)
        
        print(f"\n🔍 Decomposing query into {num_subqueries} sub-queries...")
        
        # Step 1: Decompose query
        subqueries = self.decomposer.decompose(query, num_subqueries)
        
        print(f"✓ Generated sub-queries:")
        for i, sq in enumerate(subqueries, 1):
            print(f"  {i}. {sq}")
        
        # Step 2: Execute all sub-queries in parallel
        print(f"\n🌐 Executing {len(subqueries)} FTS API calls in parallel...")
        
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_query = {
                executor.submit(call_fts_api, sq, hours, 50): sq
                for sq in subqueries
            }
            
            for future in as_completed(future_to_query):
                result = future.result()
                results.append(result)
                status = "✓" if result["success"] else "✗"
                count = len(result.get("articles", []))
                print(f"  {status} {result['subquery'][:60]}... ({count} articles)")
        
        # Step 3: Aggregate and synthesize
        print(f"\n📊 Aggregating results using '{aggregate_strategy}' strategy...")
        
        total_articles = sum(len(r.get("articles", [])) for r in results)
        successful = sum(1 for r in results if r["success"])
        
        print(f"✓ Found {total_articles} total articles across {successful}/{len(subqueries)} successful queries")
        
        print(f"\n🤖 Synthesizing comprehensive answer...")
        
        synthesis = self.aggregator.aggregate(query, results, aggregate_strategy)
        
        print(f"✓ Synthesis complete!\n")
        
        return synthesis


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """Example usage"""
    
    # Example 1: Basic usage
    print("=" * 80)
    print("EXAMPLE 1: Multi-Query Search for AI Impact")
    print("=" * 80)
    
    tool = GDELTMultiQueryFTSTool()
    
    result = tool._run(
        query="What is the impact of artificial intelligence on employment?",
        num_subqueries=5,
        hours=12
    )
    
    print("\n" + "=" * 80)
    print("FINAL RESULT:")
    print("=" * 80)
    print(result)
    
    # Example 2: Breaking news comprehensive coverage
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Breaking News Coverage")
    print("=" * 80)
    
    result = tool._run(
        query="Latest developments in US-China trade relations",
        num_subqueries=7,
        hours=24,
        aggregate_strategy="diverse"
    )
    
    print("\n" + "=" * 80)
    print("FINAL RESULT:")
    print("=" * 80)
    print(result)
    
    # Example 3: With LangChain Agent
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Integration with LangChain")
    print("=" * 80)
    
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate
    
    # Create agent
    llm = ChatOpenAI(temperature=0, model="gpt-4")
    tools = [GDELTMultiQueryFTSTool()]
    
    prompt = PromptTemplate.from_template("""
You are a news research assistant with access to GDELT's full text search.

For complex queries, use the multi_query_fts_search tool which automatically:
1. Breaks down the query into 5-10 sub-queries
2. Searches in parallel across 65 languages
3. Aggregates and synthesizes results

Tools: {tools}
Tool names: {tool_names}

Question: {input}
Thought: {agent_scratchpad}
""")
    
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    # Ask complex question
    result = agent_executor.invoke({
        "input": "Provide a comprehensive analysis of recent climate change policy developments globally, including major countries' positions and economic implications."
    })
    
    print("\n" + "=" * 80)
    print("AGENT ANSWER:")
    print("=" * 80)
    print(result["output"])


# ============================================================================
# SIMPLIFIED STANDALONE EXAMPLE
# ============================================================================

def simple_multi_query_example():
    """
    Simple standalone example showing the flow:
    User Query → Decompose → Parallel Search → Aggregate
    """
    print("\n\n" + "=" * 80)
    print("SIMPLIFIED EXAMPLE: How Multi-Query Works")
    print("=" * 80)
    
    user_query = "What are tech companies doing about AI regulation?"
    
    # Step 1: Decompose (simulated - normally uses GPT-4)
    print(f"\n1️⃣ USER QUERY: {user_query}")
    print("\n2️⃣ DECOMPOSING into sub-queries...")
    
    subqueries = [
        "tech companies AI regulation policy",
        "Microsoft Google AI safety measures",
        "artificial intelligence government regulation tech industry",
        "big tech AI ethics guidelines",
        "Silicon Valley AI regulation response"
    ]
    
    for i, sq in enumerate(subqueries, 1):
        print(f"   {i}. {sq}")
    
    # Step 2: Execute in parallel
    print("\n3️⃣ EXECUTING searches in parallel...")
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(call_fts_api, sq, 12, 20)
            for sq in subqueries
        ]
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"   ✓ Found {len(result['articles'])} articles for: {result['subquery'][:50]}...")
    
    # Step 3: Count and deduplicate
    print("\n4️⃣ AGGREGATING results...")
    
    all_articles = []
    for r in results:
        all_articles.extend(r['articles'])
    
    unique_urls = {a['url']: a for a in all_articles}
    unique_articles = list(unique_urls.values())
    
    print(f"   Total articles: {len(all_articles)}")
    print(f"   Unique articles: {len(unique_articles)}")
    print(f"   Languages: {len(set(a['lang'] for a in unique_articles))}")
    
    # Step 4: Show sample
    print("\n5️⃣ SAMPLE RESULTS (first 5):")
    for i, article in enumerate(unique_articles[:5], 1):
        print(f"\n   {i}. {article['url'][:70]}...")
        print(f"      Date: {article['date']} | Lang: {article['lang']}")
    
    print("\n6️⃣ Next step: GPT-4 would synthesize all articles into comprehensive answer")
    print("=" * 80)


if __name__ == "__main__":
    # Run simple example
    simple_multi_query_example()