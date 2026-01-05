import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_core.callbacks.base import BaseCallbackHandler
from llm_service import get_llm
from typing import Any, Dict


class ToolPrintCallback(BaseCallbackHandler):
    """Simple callback to print tool calls"""
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "Unknown")
        print(f"\n🔧 TOOL CALLED: {tool_name}")
        print(f"📥 INPUT: {input_str}\n")

async def main():
    # Initialize MCP client pointing to your server
    client = MultiServerMCPClient({
        "google_news": {
            "transport": "stdio",
            "command": "python",
            "args": ["/Users/sagarmeisheri/Documents/Streamlit-apps/OpenContext/google_news_mcp_server.py"]
        }
    })
    
    # Get tools
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from Google News server")
    print(f"Available tools: {[tool.name for tool in tools]}\n")
    
    # Create agent with LLM
    agent = create_agent(
        get_llm(temperature=0.1),
        tools,
        system_prompt='''You are a helpful assistant that can search Google News for comprehensive coverage.

IMPORTANT: For complex or multi-faceted queries, you MUST break them down and call search_google_news multiple times in parallel with different focused search terms.

Guidelines:
1. Analyze the user query first
2. If it's complex (multiple topics, broad, or asking about impacts/relationships):
   - Break it into 2-4 focused search terms (2-4 words each)
   - Call search_google_news in parallel for each term
   - CRITICAL: After all tool calls complete, you MUST synthesize all the separate results into ONE coherent, comprehensive answer
3. If it's simple (one specific topic):
   - Call search_google_news once
   - Return that result

Examples:
- Complex: "delhi air pollution and its impact"
  → Call 3x in parallel:
    • "delhi air pollution"
    • "air quality health impact"
    • "delhi pollution effects"
  → THEN: Combine all 3 results into ONE unified answer that:
    - Identifies common themes across all searches
    - Presents a cohesive narrative
    - Removes redundancy
    - Provides complete coverage of the topic

- Complex: "AI impact on employment"
  → Call 3x in parallel:
    • "AI employment"
    • "automation jobs"
    • "AI workforce impact"
  → THEN: Synthesize into ONE comprehensive answer

- Simple: "Tesla stock price"
  → Call 1x: "Tesla stock"
  → Return that result

SYNTHESIS RULES:
- Never just concatenate tool outputs
- Integrate information from all sources
- Create ONE coherent narrative
- Highlight connections between different angles
- Remove duplicate information
        '''
    )
    
    # Example query - you can modify this
    query = "with-ai-assistance-bengaluru-techie-turns-helmet-into-traffic-watchdog"
    
    print(f"Testing query: '{query}'\n")
    print("=" * 80)
    
    response = await agent.ainvoke(
        {
            "messages": [{
                "role": "user",
                "content": f"{query}"
            }]
        },
        config={"callbacks": [ToolPrintCallback()]}
    )
    
    print("\n" + "=" * 80)
    print("\nAgent Response:")
    print("=" * 80)
    print(response)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

