import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from llm_service import get_llm

async def main():
    # Initialize MCP client pointing to your server
    client = MultiServerMCPClient({
        "gdelt": {
            "transport": "stdio",
            "command": "python",
            "args": ["/Users/sagarmeisheri/Documents/Streamlit-apps/OpenContext/gdelt_mcp_server.py"]  # Update this path!
        }
    })
    
    # Get tools
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from GDELT server")
    
    # Create agent with Claude
    agent = create_agent(
        get_llm(temperature=0.1),
        tools,
        system_prompt='''You are a helpful assistant that can search the GDELT database for news articles. You can use the following tools to search the GDELT database: {tools}
        After using the tools, you should provide a summary of the results in a clear and concise manner.
        The summary should include the following information:
        - The number of articles found
        - The key themes and topics from the articles
        - The notable sources
        - The brief overview of what the articles are about
        - The DO NOT just return the raw JSON - provide an analytical summary
        - The summary should be in a clear and concise manner
        - The summary should be in a markdown format
        '''
    )
    
    # Example query
    response = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Search for recent news about us venezuela relations"
        }]
    })
    
    print(response)

# Run
asyncio.run(main())