from typing import Any
import chainlit as cl
from agents import Agent, Runner
from vector_store import search_servers, store_servers, get_all_servers
from agents.mcp import MCPServerStreamableHttp, MCPServerStdio
import asyncio
from datetime import datetime, timedelta
from local_servers import get_local_mcp_servers

# --- In-memory MCP registry per Chainlit user session ---
mcp_registry = {}

# --- Cache for MCP server list ---
_mcp_servers_cache = None
_cache_timestamp = None
_cache_ttl = timedelta(hours=24)  # Cache for 24 hours

# --- Initialize vector database on startup ---
@cl.on_chat_start
async def on_chat_start():
    """Initialize vector database with local servers if empty."""
    try:
        # Check if vector DB has any servers
        existing_servers = get_all_servers()
        if not existing_servers:
            # Populate with local servers
            local_servers = get_local_mcp_servers()
            await store_servers(local_servers)
            print(f"✅ Populated vector database with {len(local_servers)} servers")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize vector database: {e}")

async def get_mcp_servers(use_cache: bool = True) -> list[dict]:
    """
    Get a comprehensive list of MCP servers.
    
    Args:
        use_cache: Whether to use cached results
    
    Returns:
        List of MCP server dictionaries
    """
    global _mcp_servers_cache, _cache_timestamp
    
    # Check cache
    if use_cache and _mcp_servers_cache and _cache_timestamp:
        if datetime.now() - _cache_timestamp < _cache_ttl:
            return _mcp_servers_cache
    
    # Start with local curated list
    servers = get_local_mcp_servers()
    
    # Update cache
    _mcp_servers_cache = servers
    _cache_timestamp = datetime.now()
    
    return servers


# --- Intelligent recommender using agent ---
async def recommend_servers_intelligent(user_query: str) -> list[dict]:
    """Recommend MCP servers based on user query using semantic search and LLM ranking."""
    # Get candidates via semantic search, fallback to all servers if search fails
    try:
        candidate_servers = await search_servers(user_query, n_results=15)
    except Exception:
        candidate_servers = await get_mcp_servers(use_cache=True)
    
    if not candidate_servers:
        return []
    
    # Use LLM to rank and select top 3
    server_list = "\n".join([f"- {s['name']}: {s['description']}" for s in candidate_servers])
    prompt = f"""User query: "{user_query}"

Available MCP servers:
{server_list}

    Return ONLY the most relevant server name(s). Be very selective - only include servers that directly address the user's specific need.
    Return a comma-separated list (e.g., "filesystem" or "time,github" if multiple are truly needed).
    If only one server is relevant, return only that one.
    If none are relevant, return "none"."""
    
    try:
        recommender_agent = Agent[Any](name="mcp_recommender", model="gpt-4o-mini")
        result = await Runner.run(recommender_agent, prompt)
        recommendation_text = getattr(result, "final_output", None) or getattr(result, "output_text", str(result))
        
        if "none" in recommendation_text.lower():
            return candidate_servers[:3]
        
        # Match recommended names to servers
        recommended_names = {name.strip().lower() for name in recommendation_text.split(",")}
        recommended_servers = [s for s in candidate_servers if s["name"].lower() in recommended_names]
        
        return recommended_servers[:3] if recommended_servers else candidate_servers[:3]
    except Exception:
        return candidate_servers[:3]


# --- Connect to MCP server ---
async def connect_mcp_server(session_id: str, server_name: str):
    # Skip npm discovery when connecting - use local list + cache only
    servers = await get_mcp_servers(use_cache=True)
    target = next((s for s in servers if s["name"] == server_name), None)
    if not target:
        return f"❌ Server '{server_name}' not found."

    # Check if already connected
    existing_servers = mcp_registry.get(session_id, [])
    if any(s.name == server_name for s in existing_servers):
        return f"ℹ️ Server '{server_name}' is already connected."

    try:
        if target["type"] == "http":
            # (HTTP servers still use StreamableHttp)
            server = MCPServerStreamableHttp(name=target["name"], url=target["url"])
            # Increase connect timeout to handle cold starts
            await asyncio.wait_for(server.connect(), timeout=30)
            mcp_registry.setdefault(session_id, []).append(server)

        else:
            # ✅ new style: pass command/args via params
            cmd_parts = target["command"].split()
            server = MCPServerStdio(
                name=target["name"],
                params={
                    "command": cmd_parts[0],
                    "args": cmd_parts[1:]
                },
                cache_tools_list=True
            )
            server.cache_tools_list = True
            # Increase connect timeout to handle first-time npx downloads
            await asyncio.wait_for(server.connect(), timeout=30)
            mcp_registry.setdefault(session_id, []).append(server)

        # For simplicity, just list tools to verify the connection
        tools = await server.list_tools()
        tool_names = [t.name for t in tools]
        
        # Invalidate agent so it gets recreated with new servers
        cl.user_session.set("agent", None)
        
        # Format success message nicely
        tools_text = f"{len(tool_names)} tool{'s' if len(tool_names) != 1 else ''}"
        tool_list = ", ".join(tool_names[:10])  # Show first 10 tools
        if len(tool_names) > 10:
            tool_list += f", and {len(tool_names) - 10} more"
        
        return f"✅ **Successfully connected to `{server_name}` MCP server!**\n\n📦 **{tools_text} available:**\n{tool_list}"

    except Exception as e:
        return f"⚠️ Failed to connect to `{server_name}` MCP: {e}"


# --- Main Chat handler ---
@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("id")
    user_text = message.content.strip().lower()

    if session_id not in mcp_registry:
        mcp_registry[session_id] = []

    # Connect command
    if user_text.startswith("connect "):
        server_name = user_text.split(" ", 1)[1].strip()
        result_msg = await connect_mcp_server(session_id, server_name)
        await cl.Message(content=result_msg).send()
        return

    # List connected servers
    if user_text in ["list servers", "list connected", "servers", "connected"]:
        connected = mcp_registry.get(session_id, [])
        if not connected:
            await cl.Message(
                content="ℹ️ **No MCP servers connected.**\n\nAsk me something and I'll recommend some servers that could help!"
            ).send()
        else:
            server_list_parts = ["📋 **Connected MCP Servers:**\n"]
            for i, s in enumerate(connected, 1):
                try:
                    tools = await s.list_tools()
                    tool_count = len(tools)
                    tool_text = f"{tool_count} tool{'s' if tool_count != 1 else ''}"
                except Exception:
                    tool_text = "tools (unavailable)"
                server_list_parts.append(f"{i}. **{s.name}** — {tool_text}")
            await cl.Message(content="\n".join(server_list_parts)).send()
        return

    # Normal chat - with intelligent MCP server recommendations
    # Always get/create agent with current server list
    current_servers = mcp_registry.get(session_id, [])
    agent = cl.user_session.get("agent")
    
    # Recreate agent if servers changed or doesn't exist
    # Simple check: if agent doesn't exist or server count changed, recreate
    if not agent:
        agent = Agent[Any](
            name="mcp_chat_agent",
            model="gpt-4o-mini",
            mcp_servers=current_servers
        )
        cl.user_session.set("agent", agent)
    else:
        # Update agent's server list if it changed
        agent.mcp_servers = current_servers

    # Recommend MCP servers based on query intent (regardless of connected servers)
    # Track recommended servers per session to avoid repeating the same recommendations
    recommended_servers_history = cl.user_session.get("recommended_servers", set())
    
    # Get recommendations based on query intent
    recommended_servers = await recommend_servers_intelligent(message.content)
    
    if recommended_servers:
        # Filter out servers we've already recommended in this session
        # Also filter out servers that are already connected
        connected_server_names = {s.name for s in current_servers}
        new_recommendations = [
            s for s in recommended_servers 
            if s["name"] not in recommended_servers_history 
            and s["name"] not in connected_server_names
        ]
        
        # If we have new recommendations, show them
        if new_recommendations:
            server_names = [s["name"] for s in new_recommendations]
            
            # Track these recommendations so we don't show them again
            for server_name in server_names:
                recommended_servers_history.add(server_name)
            cl.user_session.set("recommended_servers", recommended_servers_history)
            
            # Create a nicely formatted recommendation message
            recommendation_parts = [
                "💡 **I think these MCP servers could help with your query:**\n"
            ]
            
            for i, server in enumerate(new_recommendations, 1):
                recommendation_parts.append(
                    f"{i}. **{server['name']}**\n   {server['description']}"
                )
            
            # Show how to connect any of the recommended servers
            if len(server_names) == 1:
                recommendation_parts.append(
                    f"\n💬 To connect this server, type: `connect {server_names[0]}`\n"
                )
            else:
                # Show examples for multiple servers
                examples = ", ".join([f"`connect {name}`" for name in server_names[:3]])
                if len(server_names) > 3:
                    examples += f", or `connect {server_names[3]}`"
                recommendation_parts.append(
                    f"\n💬 To connect a server, type: {examples}\n"
                )
            
            recommendation_parts.append(
                "ℹ️ I can still help with your query, but connecting a server will give me more capabilities!"
            )
            
            await cl.Message(content="\n".join(recommendation_parts)).send()
            return

    msg = cl.Message(content="⏳ Thinking...")
    await msg.send()

    # Small delay to make the UI feel natural
    await asyncio.sleep(0.5)

    # Replace "thinking" with an empty message for streaming
    msg.content = ""
    await msg.update()

    result = await Runner.run(agent, message.content)

    # Extract final text (depending on SDK version)
    reply = getattr(result, "final_output", str(result))

    # --- Stream tokens manually to simulate live typing ---
    for token in reply.split():
        await msg.stream_token(token + " ")
        await asyncio.sleep(0.02)  # small delay for effect

    # Mark the message as complete
    await msg.update()
