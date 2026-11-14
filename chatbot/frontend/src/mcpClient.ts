import { Client } from "@modelcontextprotocol/sdk/client/index";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const transport = new StreamableHTTPClientTransport(
  new URL("http://localhost:8000/mcp"),
);

const mcpClient = new Client(
  {
    name: "chatbot-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {},
  },
);

export async function connectToMcp() {
  try {
    await mcpClient.connect(transport);
    console.log("Connected to FastAPI MCP server successfully");

    const toolsResponse = await mcpClient.listTools();
    console.log("Available tools: ", toolsResponse.tools);
    return mcpClient;
  } catch (error) {
    console.error("Failed to connect to MCP server: ", error);
  }
}

// Helper function to invoke a tool (like a fastapi route) from react
export async function callMcpTool(toolName, argumentsObj) {
  return await mcpClient.callTool({
    name: toolName,
    arguments: argumentsObj,
  });
}

export async function getAvailableTools() {
  try {
    const toolsResponse = await mcpClient.listTools();
    return toolsResponse.tools || [];
  } catch (error) {
    console.error("Failed to fetch available tools: ", error);
    return [];
  }
}