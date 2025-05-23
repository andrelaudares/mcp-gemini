Okay, here is a refracted, hyper-explanatory summary of the provided `como-construir-mcp.txt` context, focusing on the essential information needed for an AI coding assistant to **build an MCP server or client using FastMCP v2.0**. Insignificant details for this specific purpose (like CI config, detailed lock files, issue templates) are omitted.

**Core Concept: FastMCP v2.0**

FastMCP is a Python framework designed to simplify the creation of **Model Context Protocol (MCP)** servers and clients. It handles the underlying MCP protocol complexity, allowing developers to define functionality using Pythonic decorators and standard Python types. Version 2.0 significantly expands on v1.0 (found in the official `mcp` SDK) by adding robust client capabilities, server composition, proxying, and more.

**Key Components for Building:**

1.  **The `FastMCP` Server (`fastmcp.FastMCP`)**:
    *   **Central Object**: This is the main class you instantiate to create your MCP server (`mcp = FastMCP(name="MyServer")`).
    *   **Container**: It holds all your Tools, Resources, and Prompts.
    *   **Configuration**: Takes optional `name`, `instructions`, `lifespan` context manager, `tags`, and other settings (like `auth_provider`).

2.  **Tools (`@mcp.tool()`)**:
    *   **Purpose**: Define actions the LLM can request (like API calls, calculations, side effects - similar to `POST`/`PUT`).
    *   **Definition**: Decorate regular Python functions (sync or `async`) with `@mcp.tool()`.
    *   **Schema**: Function parameters and type hints are automatically converted into the input schema for the LLM. Docstrings become descriptions.
    *   **Return Values**: Can return strings, JSON-serializable objects (dicts, lists, Pydantic models), `bytes`, `fastmcp.Image`, or `None`. Non-string results are typically JSON-serialized by default (customizable via `tool_serializer`).
    *   **Example**:
        ```python
        from fastmcp import FastMCP

        mcp = FastMCP()

        @mcp.tool()
        def add(a: int, b: int) -> int:
            """Adds two numbers."""
            return a + b
        ```

3.  **Resources & Templates (`@mcp.resource()`)**:
    *   **Purpose**: Expose read-only data sources to the LLM (similar to `GET`).
    *   **Definition**: Decorate Python functions (sync or `async`) with `@mcp.resource("your://uri")`.
    *   **Static Resources**: If the function takes no arguments *and* the URI has no `{placeholders}`, it's a static resource. The function runs when the URI is requested.
    *   **Resource Templates**: If the URI *contains* `{placeholders}` (e.g., `users://{user_id}/profile`) and the function accepts corresponding arguments (e.g., `def get_profile(user_id: str)`), it defines a template. The placeholders become parameters. Wildcard parameters (`{path*}`) are also supported.
    *   **Return Values**: Similar to tools (str, dict, list, bytes, Pydantic models). Dicts/lists/models become JSON text.
    *   **Example**:
        ```python
        @mcp.resource("config://version") # Static
        def get_version(): return "2.1.0"

        @mcp.resource("users://{user_id}") # Template
        def get_user(user_id: int): return {"id": user_id, "name": f"User {user_id}"}
        ```

4.  **Prompts (`@mcp.prompt()`)**:
    *   **Purpose**: Define reusable, parameterized message templates to guide LLM interactions.
    *   **Definition**: Decorate Python functions (sync or `async`) with `@mcp.prompt()`.
    *   **Return Values**: Can return `str` (becomes a user message), `PromptMessage` object (from `mcp.types` or `fastmcp.prompts.prompt.Message`), or a `list` of these for multi-turn prompts.
    *   **Example**:
        ```python
        from fastmcp.prompts.prompt import Message

        @mcp.prompt()
        def summarize(text: str) -> list[Message]:
            return [Message(f"Please summarize: {text}")]
        ```

5.  **Context (`ctx: Context`)**:
    *   **Purpose**: Access MCP session capabilities within Tools, Resources, or Prompts.
    *   **Usage**: Add a parameter type-hinted as `Context` (e.g., `ctx: Context`) to your decorated function signature. FastMCP injects it automatically.
    *   **Capabilities**:
        *   Logging: `await ctx.info("Log message")`, `ctx.error(...)`, etc.
        *   Resource Reading: `content = await ctx.read_resource("your://uri")`.
        *   LLM Sampling: `response = await ctx.sample("Ask the client's LLM...")`.
        *   Progress: `await ctx.report_progress(50, 100)`.
        *   Request Info: `ctx.request_id`, `ctx.client_id`.
        *   HTTP Request (Web context only): `request = get_http_request()` via `fastmcp.server.dependencies`.

6.  **The `Client` (`fastmcp.Client`)**:
    *   **Purpose**: Programmatically interact with *any* MCP server (FastMCP or other).
    *   **Usage**: Asynchronous context manager: `async with Client(target) as client: ...`.
    *   **Target**: Can be a `FastMCP` server instance (for in-memory testing), a file path (`.py`, `.js`), a URL (`http://`, `https://` for SSE, `ws://`, `wss://` for WebSocket). Transports are often inferred.
    *   **Methods**: `await client.list_tools()`, `await client.call_tool("name", {"arg": val})`, `await client.read_resource("uri")`, `await client.get_prompt("name", {...})`. Also `*_mcp` variants for raw protocol objects.
    *   **Callbacks**: Can provide handlers for server-initiated actions like logging (`log_handler`) and LLM sampling (`sampling_handler`).

**Running the Server:**

*   **Development (`fastmcp dev`)**: Interactive testing with MCP Inspector. `fastmcp dev server.py`
*   **CLI (`fastmcp run`)**: General purpose runner. `fastmcp run server.py:mcp --transport sse --port 8080`. Auto-detects `mcp`, `app`, `server` objects if name isn't specified.
*   **Direct (`python server.py`)**: Most compatible way. Requires `if __name__ == "__main__": mcp.run()` in the script. `mcp.run()` defaults to `stdio`, `mcp.run(transport="sse", ...)` for SSE.
*   **Claude Install (`fastmcp install`)**: Easiest way for Claude Desktop integration. Creates isolated env. `fastmcp install server.py --name "My Tool"`.

**Advanced Server Patterns:**

*   **Composition**: Combine servers.
    *   `mcp.import_server("prefix", sub_server)`: Static copy, adds prefixes.
    *   `mcp.mount("prefix", sub_server)`: Live link, delegates requests.
*   **Proxying**: `FastMCP.from_client(client)` creates a server that forwards requests to the server the `client` connects to. Useful for bridging transports.
*   **OpenAPI/FastAPI**: `FastMCP.from_openapi(spec, client)` or `FastMCP.from_fastapi(app)` automatically generate MCP servers from web APIs.

**Project Setup:**

*   **Installation**: `uv pip install fastmcp` (or `pip install fastmcp`).
*   **Dependencies**: Defined in `pyproject.toml`. Key deps include `mcp`, `httpx`, `pydantic`. FastAPI/OpenAPI integration requires installing `fastapi` or `openapi-pydantic` separately.

This summary provides the core knowledge needed to start building MCP components with FastMCP. Refer to the `examples/` directory for practical code and the `docs/` for more in-depth explanations of each feature. The `src/` directory contains the implementation details.