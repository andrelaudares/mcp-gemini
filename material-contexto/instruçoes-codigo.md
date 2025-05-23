Okay, let's break down how to build this FastMCP server for interacting with the Omie API.

Based on your request and the provided context (Omie API documentation snippets and Postman screenshots), the goal is to create an MCP server that can:

1.  Accept input like CNPJ, Fantasy Name, or City to identify a customer.
2.  Use the Omie `ListarClientes` API endpoint to find the `codigo_cliente_omie` based on the input.
3.  Use the retrieved `codigo_cliente_omie` to call the Omie `ListarPedidos` API endpoint.
4.  Process the list of orders and return information about the last 3 orders (e.g., item details).

We will use FastMCP to create a **Tool** that encapsulates this workflow. A tool is suitable because it represents an *action* the user (or an LLM agent) wants to perform based on specific input, resulting in fetched and processed data.

Here are the two approaches you requested:

## Approach 1: Detailed Explanatory Document

This document outlines the steps and considerations for building the MCP server. You can use this as a guide for development or as context for your AI coding assistant.

---

### **Building an Omie Integration MCP Server with FastMCP**

**1. Goal:**

Create a FastMCP server that provides a tool to find a customer in Omie using CNPJ, Fantasy Name, or City, and then list their last 3 sales orders.

**2. Prerequisites:**

*   Python installed (>= 3.10 recommended for FastMCP).
*   A tool to manage Python environments and packages (like `uv` or `pip`).
*   Omie API Credentials (`app_key`, `app_secret`). **Treat these as sensitive data.**
*   Basic understanding of FastMCP concepts (Server, Tool). Refer to the `jlowin-fastmcp` README or documentation (`gofastmcp.com`).

**3. Project Setup:**

*   Create a new project directory (e.g., `omie_mcp_server`).
*   Inside the directory, create a `pyproject.toml` file to manage dependencies:
    ```toml
    [project]
    name = "omie_mcp_server"
    version = "0.1.0"
    description = "FastMCP server for Omie API integration."
    requires-python = ">=3.10"
    dependencies = [
        "fastmcp",
        "httpx",          # For making HTTP requests to Omie API
        "pydantic",       # Used by FastMCP and good for data modeling
        "pydantic-settings", # For managing configuration/secrets
        "python-dotenv"   # To load .env files
    ]

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"
    ```
*   Install dependencies using `uv sync` or `uv pip install -r requirements.txt` (if you create one from the `pyproject.toml`).
*   Create a `.env` file in the project root to store your Omie credentials securely:
    ```dotenv
    OMIE_APP_KEY=YOUR_OMIE_APP_KEY
    OMIE_APP_SECRET=YOUR_OMIE_APP_SECRET
    ```
    *Ensure this `.env` file is added to your `.gitignore` if using version control.*

**4. Configuration Management:**

*   Create a `config.py` (or similar) file to load settings using `pydantic-settings`. This keeps credentials separate from your main code.

    ```python
    # config.py
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file='.env', extra='ignore')

        omie_app_key: str
        omie_app_secret: str
        omie_api_base_url: str = "https://app.omie.com.br/api/v1"

    settings = Settings()
    ```

**5. Designing the MCP Tool:**

*   We need one primary tool, let's call it `find_customer_orders`.
*   **Inputs:** It needs to accept *at least one* of the search criteria. We'll make them optional strings.
    *   `cnpj_cpf: str | None = None`
    *   `nome_fantasia: str | None = None`
    *   `cidade: str | None = None`
*   **Validation:** The tool logic must ensure that the user provided at least one input parameter.
*   **Return Value:** It should return information about the last 3 orders. A list of dictionaries is a good starting point. Each dictionary could contain order details like `numero_pedido`, `data_previsao`, and selected item information (`descricao`, `quantidade`, `valor_total`). Define a Pydantic model later for better structure if needed.
*   **Description:** Provide a clear docstring explaining what the tool does, its parameters, and what it returns.

**6. Implementing the Tool Logic (`server.py`):**

*   Import necessary modules: `FastMCP`, `httpx`, `Optional`, `List`, `Dict`, `Any`, your `config.settings`.
*   Instantiate the `FastMCP` server: `mcp = FastMCP("Omie Integration Server")`
*   Define the `find_customer_orders` function and decorate it with `@mcp.tool()`:

    ```python
    # server.py (simplified structure)
    from typing import Optional, List, Dict, Any
    import httpx
    from fastmcp import FastMCP
    from config import settings # Assuming you created config.py

    mcp = FastMCP("Omie Integration Server")

    # Define helper function for API calls (recommended)
    async def call_omie_api(endpoint: str, call_name: str, params: List[Dict[str, Any]]) -> Dict[str, Any]:
        api_url = f"{settings.omie_api_base_url}{endpoint}"
        payload = {
            "call": call_name,
            "app_key": settings.omie_app_key,
            "app_secret": settings.omie_app_secret,
            "param": params
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(api_url, json=payload, timeout=30.0)
                response.raise_for_status() # Raise exception for 4xx/5xx errors
                return response.json()
            except httpx.HTTPStatusError as e:
                # Log error, return structured error info
                print(f"Omie API Error ({e.response.status_code}): {e.response.text}")
                # Return error details to the tool to handle
                return {"error": True, "status_code": e.response.status_code, "message": e.response.text}
            except httpx.RequestError as e:
                print(f"Omie Request Error: {e}")
                return {"error": True, "status_code": None, "message": str(e)}
            except Exception as e: # Catch other potential errors like JSONDecodeError
                print(f"Unexpected Error calling Omie API: {e}")
                return {"error": True, "status_code": None, "message": "Unexpected API processing error"}

    @mcp.tool()
    async def find_customer_orders(
        cnpj_cpf: Optional[str] = None,
        nome_fantasia: Optional[str] = None,
        cidade: Optional[str] = None
    ) -> List[Dict[str, Any]] | str:
        """
        Finds a customer using CNPJ/CPF, Fantasy Name, or City and returns their last 3 orders.
        Provide at least one search parameter.
        """
        # 1. Input Validation
        if not any([cnpj_cpf, nome_fantasia, cidade]):
            return "Error: Please provide at least one search parameter (CNPJ/CPF, Fantasy Name, or City)."

        # 2. Find Customer ID using ListarClientes
        cliente_filter = {}
        if cnpj_cpf:
            cliente_filter["cnpj_cpf"] = cnpj_cpf
        if nome_fantasia:
            cliente_filter["nome_fantasia"] = nome_fantasia
        if cidade:
            cliente_filter["cidade"] = cidade # Assumes 'cidade' is a valid filter key

        listar_clientes_params = [{
            "pagina": 1,
            "registros_por_pagina": 2, # Request 2 to detect multiple matches
            "apenas_importado_api": "N",
            "clientesFiltro": cliente_filter
        }]

        cliente_response = await call_omie_api("/geral/clientes/", "ListarClientes", listar_clientes_params)

        if cliente_response.get("error"):
            return f"Error finding customer: {cliente_response.get('message', 'Unknown API error')}"
        if not cliente_response.get("clientes_cadastro"):
             return "Error: Customer not found."
        if cliente_response.get("total_de_registros", 0) > 1:
             return "Error: Multiple customers found. Please provide more specific criteria."

        # 3. Extract Customer ID
        try:
            customer_id = cliente_response["clientes_cadastro"][0]["codigo_cliente_omie"]
        except (IndexError, KeyError):
             return "Error: Could not extract customer ID from Omie response."

        # 4. Find Orders using ListarPedidos
        listar_pedidos_params = [{
            "pagina": 1,
            "registros_por_pagina": 50, # Fetch more to sort/filter locally if needed
            "apenas_importado_api": "N",
            "filtrar_por_cliente": customer_id
        }]

        pedidos_response = await call_omie_api("/produtos/pedido/", "ListarPedidos", listar_pedidos_params)

        if pedidos_response.get("error"):
            return f"Error fetching orders: {pedidos_response.get('message', 'Unknown API error')}"
        if not pedidos_response.get("pedido_venda_produto"):
             return "No orders found for this customer."

        # 5. Process Orders
        orders = pedidos_response.get("pedido_venda_produto", [])
        # Assuming the API returns orders most recent first, otherwise sorting is needed.
        recent_orders = orders[:3]

        # 6. Format Output
        formatted_orders = []
        for order in recent_orders:
            order_info = {
                "numero_pedido": order.get("cabecalho", {}).get("numero_pedido"),
                "data_previsao": order.get("cabecalho", {}).get("data_previsao"),
                "total_pedido": order.get("total_pedido", {}).get("valor_total_pedido"),
                "itens": []
            }
            for item in order.get("det", []):
                item_info = {
                    "descricao": item.get("produto", {}).get("descricao"),
                    "quantidade": item.get("produto", {}).get("quantidade"),
                    "valor_total_item": item.get("produto", {}).get("valor_total")
                }
                order_info["itens"].append(item_info)
            formatted_orders.append(order_info)

        return formatted_orders

    # Add the standard run block
    if __name__ == "__main__":
        mcp.run()

    ```

**7. Running the Server:**

*   Make sure your `.env` file is present and correct.
*   Run the server from your terminal: `python server.py`
*   The server will start listening on standard input/output (the default `stdio` transport), ready for a client (like Claude Desktop or a custom script using `fastmcp.Client`) to connect.

**8. Testing (Example using FastMCP Client):**

*   Create a separate `client_test.py`:

    ```python
    # client_test.py
    import asyncio
    from fastmcp import Client

    async def main():
        # Connects to the server running via 'python server.py'
        async with Client("server.py") as client:
            print("Listing tools...")
            tools = await client.list_tools()
            print(f"Found tools: {[t.name for t in tools]}")

            print("\nCalling find_customer_orders with CNPJ...")
            # Replace with a valid CNPJ for testing
            result_cnpj = await client.call_tool("find_customer_orders", {"cnpj_cpf": "YOUR_TEST_CNPJ"})
            print("Result (CNPJ):", result_cnpj)

            # Add more calls with nome_fantasia, cidade etc.

    if __name__ == "__main__":
        asyncio.run(main())
    ```
*   Run the server first (`python server.py`), then in another terminal, run the client (`python client_test.py`).

**9. Next Steps/Refinements:**

*   **Error Handling:** Improve error checking from API responses (check for specific Omie error codes/messages).
*   **Data Modeling:** Use Pydantic models for the `find_customer_orders` return value instead of `List[Dict]`.
*   **Async:** Ensure all potentially blocking operations (like `httpx` calls) use `await`. The example uses `async` already.
*   **Sorting/Filtering Orders:** If the API doesn't return orders sorted by date, you'll need to fetch more results and sort/filter them within the tool function. This requires knowing which date field to use for sorting.
*   **Logging:** Add proper logging using `fastmcp.utilities.logging` or the `Context` object within the tool.
*   **Parameter Exclusivity:** Add logic to ensure *only one* of cnpj_cpf, nome_fantasia, or cidade is used if that's the desired behavior, or handle precedence if multiple are provided.

---

## Approach 2: Code Skeleton

This provides a starting Python code structure. You or your AI assistant will need to fill in the details, especially the API interaction logic.

```python
# server.py
import asyncio
from typing import Optional, List, Dict, Any
import httpx
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastmcp import FastMCP
# If you plan to use Context for logging/etc, import it:
# from fastmcp import Context

# --- Configuration ---
class Settings(BaseSettings):
    # Load settings from .env file, case-insensitive keys
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)

    omie_app_key: str = Field(..., alias='OMIE_APP_KEY')
    omie_app_secret: str = Field(..., alias='OMIE_APP_SECRET')
    omie_api_base_url: str = "https://app.omie.com.br/api/v1"

# Load settings - will raise error if .env is missing or vars aren't set
try:
    settings = Settings()
except ValidationError as e:
    print(f"Error loading settings. Ensure .env file exists and contains OMIE_APP_KEY and OMIE_APP_SECRET.\n{e}")
    exit(1)

# --- FastMCP Server Setup ---
mcp = FastMCP("Omie Integration Server")

# --- Helper Function for Omie API Calls ---
async def call_omie_api(endpoint_path: str, call_name: str, params: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Helper function to make POST requests to the Omie API.

    Args:
        endpoint_path: The specific API endpoint path (e.g., "/geral/clientes/").
        call_name: The Omie API call name (e.g., "ListarClientes").
        params: The list of parameters for the 'param' key in the Omie payload.

    Returns:
        A dictionary containing the JSON response from the API or an error dictionary.
    """
    api_url = f"{settings.omie_api_base_url}{endpoint_path}"
    payload = {
        "call": call_name,
        "app_key": settings.omie_app_key,
        "app_secret": settings.omie_app_secret,
        "param": params
    }
    # Consider adding headers if required by Omie, e.g., {'Content-Type': 'application/json'}
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            print(f"Calling Omie API: {call_name} at {api_url}") # Basic logging
            # print(f"Payload: {json.dumps(payload, indent=2)}") # Uncomment for debugging payload
            response = await client.post(api_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            response_json = response.json()
            # print(f"Response JSON: {json.dumps(response_json, indent=2)}") # Uncomment for debugging response
            # Omie specific error check (if applicable - adjust based on actual API errors)
            if response_json.get('faultstring') or response_json.get('faultcode'):
                 print(f"Omie API Error Response: {response_json}")
                 return {"error": True, "status_code": response.status_code, "message": response_json.get('faultstring', 'Unknown Omie Error')}
            return response_json
        except httpx.HTTPStatusError as e:
            # Log error, return structured error info
            print(f"Omie HTTP Status Error ({e.response.status_code}): {e.response.text}")
            return {"error": True, "status_code": e.response.status_code, "message": e.response.text}
        except httpx.RequestError as e:
            print(f"Omie Request Error: {e}")
            return {"error": True, "status_code": None, "message": str(e)}
        except json.JSONDecodeError as e:
            print(f"Omie JSON Decode Error: {e}. Response text: {response.text}")
            return {"error": True, "status_code": response.status_code, "message": "Failed to decode Omie API response"}
        except Exception as e: # Catch other potential errors
            print(f"Unexpected Error calling Omie API: {e}")
            return {"error": True, "status_code": None, "message": "Unexpected API processing error"}


# --- The Main Tool ---
@mcp.tool()
async def find_customer_orders(
    cnpj_cpf: Optional[str] = Field(None, description="CNPJ or CPF of the customer."),
    nome_fantasia: Optional[str] = Field(None, description="Fantasy name of the customer."),
    cidade: Optional[str] = Field(None, description="City of the customer.")
    # Optional: Add Context parameter if logging/etc. is needed: ctx: Context
) -> List[Dict[str, Any]] | str:
    """
    Finds a customer using CNPJ/CPF, Fantasy Name, or City, then fetches and returns
    details about their last 3 sales orders from the Omie API.
    Requires at least one search parameter (cnpj_cpf, nome_fantasia, or cidade).
    Returns a list of order details or an error message string.
    """
    # 1. --- Input Validation ---
    if not any([cnpj_cpf, nome_fantasia, cidade]):
        return "Error: Please provide at least one search parameter (CNPJ/CPF, Fantasy Name, or City)."
    print(f"Searching for customer with: CNPJ/CPF='{cnpj_cpf}', Name='{nome_fantasia}', City='{cidade}'")

    # 2. --- Find Customer ID (Call ListarClientes) ---
    print("Finding customer ID...")
    cliente_filter = {}
    if cnpj_cpf:
        cliente_filter["cnpj_cpf"] = cnpj_cpf
    if nome_fantasia:
        cliente_filter["nome_fantasia"] = nome_fantasia
    if cidade:
        # Ensure 'cidade' is the correct filter key based on Omie docs/your testing
        cliente_filter["cidade"] = cidade

    listar_clientes_params = [{
        "pagina": 1,
        "registros_por_pagina": 2, # Request 2 to detect multiple matches
        "apenas_importado_api": "N", # As per your example image
        "clientesFiltro": cliente_filter
    }]

    cliente_response = await call_omie_api("/geral/clientes/", "ListarClientes", listar_clientes_params)

    # --- Handle ListarClientes Response ---
    if cliente_response.get("error"):
        return f"Error finding customer: {cliente_response.get('message', 'Unknown API error')}"
    if not cliente_response.get("clientes_cadastro"):
        return "Error: Customer not found with the provided criteria."
    if cliente_response.get("total_de_registros", 0) > 1:
        return f"Error: Multiple customers ({cliente_response['total_de_registros']}) found. Please provide more specific criteria."

    # 3. --- Extract Customer ID ---
    try:
        customer_id = cliente_response["clientes_cadastro"][0]["codigo_cliente_omie"]
        print(f"Found customer ID: {customer_id}")
    except (IndexError, KeyError, TypeError) as e:
        print(f"Error extracting customer ID: {e}. Response: {cliente_response}")
        return "Error: Could not extract customer ID from Omie response."

    # 4. --- Find Orders (Call ListarPedidos) ---
    print(f"Fetching orders for customer ID: {customer_id}...")
    listar_pedidos_params = [{
        "pagina": 1,
        "registros_por_pagina": 50, # Fetch a decent number, filter later
        "apenas_importado_api": "N",
        "filtrar_por_cliente": customer_id
        # Add other filters if needed, e.g., date range, status
        # "ordenar_por": "DATA_INCLUSAO" # Check if API supports sorting
    }]

    pedidos_response = await call_omie_api("/produtos/pedido/", "ListarPedidos", listar_pedidos_params)

    # --- Handle ListarPedidos Response ---
    if pedidos_response.get("error"):
        return f"Error fetching orders: {pedidos_response.get('message', 'Unknown API error')}"
    if not pedidos_response.get("pedido_venda_produto"):
        return f"No orders found for customer ID: {customer_id}."

    # 5. --- Process Orders ---
    print("Processing orders...")
    orders = pedidos_response.get("pedido_venda_produto", [])
    # Assuming the API returns orders somewhat chronologically (most recent first is common)
    # If not, you'll need a date field to sort by. Let's take the first 3 for now.
    recent_orders = orders[:3]

    # 6. --- Format Output ---
    print(f"Formatting the latest {len(recent_orders)} orders...")
    formatted_orders = []
    for order in recent_orders:
        # Extract relevant details - Adjust keys based on actual Omie response structure
        cabecalho = order.get("cabecalho", {})
        total_pedido_info = order.get("total_pedido", {})
        itens_list = []
        for item in order.get("det", []):
            produto_info = item.get("produto", {})
            itens_list.append({
                "descricao": produto_info.get("descricao", "N/A"),
                "quantidade": produto_info.get("quantidade", 0),
                "valor_unitario": produto_info.get("valor_unitario", 0.0),
                "valor_total_item": produto_info.get("valor_total", 0.0) # Adjust if key is different
            })

        formatted_orders.append({
            "numero_pedido": cabecalho.get("numero_pedido", "N/A"),
            "data_previsao": cabecalho.get("data_previsao", "N/A"),
            "etapa": cabecalho.get("etapa", "N/A"),
            "valor_total_pedido": total_pedido_info.get("valor_total_pedido", 0.0),
            "itens": itens_list
        })

    print(f"Formatted orders: {len(formatted_orders)}")
    return formatted_orders

# --- Standard Run Block ---
if __name__ == "__main__":
    print("Starting Omie Integration MCP Server...")
    # This runs the server using the default stdio transport
    # Accessible by clients like Claude Desktop or custom scripts
    mcp.run()
```

**To use this code:**

1.  Save it as `server.py`.
2.  Create the `config.py` file as shown in Approach 1.
3.  Create the `.env` file with your Omie credentials.
4.  Install dependencies: `uv pip install fastmcp httpx pydantic pydantic-settings python-dotenv`
5.  Run the server: `python server.py`

This skeleton provides the structure. You'll need to ensure the API endpoint paths, call names, parameter keys (`clientesFiltro`, `filtrar_por_cliente`, etc.), and response keys (`codigo_cliente_omie`, `pedido_venda_produto`, etc.) exactly match the Omie API documentation and your testing results. The helper function `call_omie_api` includes basic error handling, which should be expanded.

Choose the approach that works best for you. The explanatory document provides the reasoning, while the code skeleton gives a direct starting point. Good luck!