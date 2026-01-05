import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
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
    query = "manchester united sack theri maanger who is next"
    
    print(f"Testing query: '{query}'\n")
    print("=" * 80)
    
    response = await agent.ainvoke(
        {
            "messages": [{
                "role": "user",
                "content": f"{query}"
            }]
        },
        # config={"callbacks": [ToolPrintCallback()]}
    )
    
    # Extract and print all messages by type
    messages = response.get("messages", [])
    print(f"\n📬 AGENT EXECUTION FLOW ({len(messages)} messages)")
    print("=" * 100)
    
    for idx, msg in enumerate(messages, 1):
        
        if isinstance(msg, HumanMessage):
            print(f"\n[{idx}] 🧑 USER QUERY")
            print(f"    \"{msg.content}\"")
            
        elif isinstance(msg, AIMessage):
            # Check if this is an intermediate AI message (with tool calls) or final response
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"\n[{idx}] 🤖 AI DECISION: Call {len(msg.tool_calls)} tool(s)")
                for i, tc in enumerate(msg.tool_calls, 1):
                    print(f"    └─ Tool #{i}: {tc.get('name')}(query=\"{tc.get('args', {}).get('query')}\")")
            else:
                # Final AI response with actual content
                print(f"\n[{idx}] 🤖 AI FINAL ANSWER")
                print("-" * 100)
                if msg.content:
                    # Print full content for final answer
                    print(msg.content)
                else:
                    print("(empty response)")
                print("-" * 100)
                
                # Show token usage if available
                if hasattr(msg, 'response_metadata') and 'token_usage' in msg.response_metadata:
                    usage = msg.response_metadata['token_usage']
                    print(f"    📊 Tokens: {usage.get('total_tokens')} total "
                          f"({usage.get('prompt_tokens')} prompt + {usage.get('completion_tokens')} completion)")
            
        elif isinstance(msg, ToolMessage):
            print(f"\n[{idx}] 🔧 TOOL RESULT")
            
            # Show tool call ID
            if hasattr(msg, 'tool_call_id'):
                print(f"    Tool Call ID: {msg.tool_call_id[:20]}...")
            
            # Get content - could be string or list of dicts
            content = msg.content
            if isinstance(content, list) and len(content) > 0:
                # Extract text from first item
                text_content = content[0].get('text', '') if isinstance(content[0], dict) else str(content[0])
            else:
                text_content = str(content)
            
            # Show preview of content
            lines = text_content.split('\n')
            preview_lines = lines[:3]  # First 3 lines
            print(f"    Content preview ({len(text_content)} chars, {len(lines)} lines):")
            for line in preview_lines:
                if line.strip():
                    print(f"      {line[:90]}...")
            
            # Show if there's structured content in artifact
            if hasattr(msg, 'artifact') and msg.artifact:
                print(f"    ✓ Structured artifact available")
        
        else:
            print(f"\n[{idx}] ❓ {type(msg).__name__}")
            print(f"    Content: {msg.content if hasattr(msg, 'content') else 'N/A'}")
    
    print("\n" + "=" * 100)
    
    # print("\n" + "=" * 80)
    # print("\nAgent Response:")
    # print("=" * 80)
    # print(response)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

