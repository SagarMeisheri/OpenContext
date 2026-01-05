import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from llm_service import get_llm

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
        system_prompt='''You are a helpful assistant that can search Google News for recent headlines. 
        
        When you use the get_news_headlines tool, you will receive:
        - A list of recent news articles with titles, sources, and publication dates
        
        summarize the news across all the headlines in a clear and concise manner.
        '''
    )
    
    # Example query - you can modify this
    query = "US Military Operation & Capture of Nicolás Maduro"
    
    print(f"Testing query: '{query}'\n")
    print("=" * 80)
    
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": f"What's happening with {query} in the news recently?"
        }]
    })
    
    print("\n" + "=" * 80)
    print("\nAgent Response:")
    print("=" * 80)
    print(response)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

