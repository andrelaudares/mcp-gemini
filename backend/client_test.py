import asyncio
from fastmcp import Client

async def main():
    # Conecta-se ao server.py.
    # Quando usamos Client("server.py"), ele tentará executar 'python server.py'
    # como um subprocesso.
    print("Tentando conectar ao servidor MCP em server.py...")
    try:
        async with Client("server.py") as client:
            print("Conectado! Listando ferramentas...")
            tools = await client.list_tools()
            if not tools:
                print("Nenhuma ferramenta encontrada no servidor.")
                return

            tool_names = [t.name for t in tools]
            print(f"Ferramentas encontradas: {tool_names}")

            if "responder_pergunta_sobre_pedidos" not in tool_names:
                print("ERRO: A ferramenta 'responder_pergunta_sobre_pedidos' não foi encontrada no servidor.")
                if "encontrar_pedidos_cliente" in tool_names:
                    print("INFO: A ferramenta 'encontrar_pedidos_cliente' FOI encontrada.")
                return

            pergunta_ia_teste = "Quanto gastei no último produto que comprei com o CNPJ 359.489.811-34?"
            print(f"\n--- Chamando responder_pergunta_sobre_pedidos com a pergunta: ---")
            print(f"'{pergunta_ia_teste}'")
            
            params_ia = {"pergunta_usuario": pergunta_ia_teste}
            
            result_ia = await client.call_tool("responder_pergunta_sobre_pedidos", params_ia)
            print("\nResultado da chamada à ferramenta de IA:")

            if result_ia and hasattr(result_ia, 'text') and isinstance(result_ia.text, str):
                 print(result_ia.text)
            elif isinstance(result_ia, str):
                print(result_ia)
            else:
                print(result_ia)

    except Exception as e:
        print(f"Ocorreu um erro durante o teste do cliente: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
