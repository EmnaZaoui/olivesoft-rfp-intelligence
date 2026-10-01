import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

from app.config import settings


async def _call_tool_async(tool_name: str, arguments: dict) -> str:
    async with sse_client(settings.mcp_server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(texts) if texts else "Aucun résultat retourné par l'outil."


def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Wrapper synchrone pour appeler un outil MCP depuis le code de l'agent (LangGraph)."""
    try:
        return asyncio.run(_call_tool_async(tool_name, arguments))
    except Exception as e:
        return f"MCP_TOOL_ERROR: {e}"