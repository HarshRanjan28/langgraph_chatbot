
import asyncio
from langchain.mcp import MCPAdapter

async def main():

    async with MCPAdapter(
        "http://127.0.0.1:8000/mcp/"
    ) as adapter:

        tools = await adapter.list_tools()

        print("\n========== MCP TOOLS ==========")

        for tool in tools:
            print(f"Name: {tool.name}")
            print(f"Description: {tool.description}")
            print("------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
