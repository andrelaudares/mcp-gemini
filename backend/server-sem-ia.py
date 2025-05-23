import asyncio
import json # Adicionado para debugging
from typing import Optional, List, Dict, Any

import httpx
from pydantic import Field

from fastmcp import FastMCP
# from fastmcp import Context # Descomente se for usar o Contexto para logging avançado, etc.

# --- Configuration ---
# Importa as configurações do config.py
# Presume que config.py está no mesmo diretório ou no PYTHONPATH
from backend.config import settings

# --- FastMCP Server Setup ---
mcp = FastMCP("Servidor de Integração Omie")

# --- Helper Function for Omie API Calls ---
async def call_omie_api(endpoint_path: str, call_name: str, params: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Função auxiliar para fazer requisições POST para a API Omie.

    Args:
        endpoint_path: O caminho específico do endpoint da API (ex: "/geral/clientes/").
        call_name: O nome da chamada da API Omie (ex: "ListarClientes").
        params: A lista de parâmetros para a chave 'param' no payload Omie.

    Returns:
        Um dicionário contendo a resposta JSON da API ou um dicionário de erro.
    """
    api_url = f"{settings.omie_api_base_url}{endpoint_path}"
    payload = {
        "call": call_name,
        "app_key": settings.omie_app_key,
        "app_secret": settings.omie_app_secret,
        "param": params
    }
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            print(f"Chamando API Omie: {call_name} em {api_url}") # Log básico
            # print(f"Payload: {json.dumps(payload, indent=2)}") # Descomente para depurar o payload
            response = await client.post(api_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status() # Levanta exceção para erros 4xx/5xx
            response_json = response.json()
            # print(f"Response JSON: {json.dumps(response_json, indent=2)}") # Descomente para depurar a resposta
            
            # Verificação de erro específica da Omie (algumas APIs Omie retornam erros dentro de um JSON com status 200)
            if response_json.get('faultstring') or response_json.get('faultcode'):
                 print(f"Erro na API Omie (resposta): {response_json}")
                 return {"error": True, "status_code": response.status_code, "message": response_json.get('faultstring', 'Erro desconhecido da Omie')}
            return response_json
        except httpx.HTTPStatusError as e:
            print(f"Erro de Status HTTP Omie ({e.response.status_code}): {e.response.text}")
            return {"error": True, "status_code": e.response.status_code, "message": e.response.text}
        except httpx.RequestError as e:
            print(f"Erro de Requisição Omie: {e}")
            return {"error": True, "status_code": None, "message": str(e)}
        except json.JSONDecodeError as e:
            print(f"Erro de Decodificação JSON Omie: {e}. Texto da resposta: {response.text if hasattr(response, 'text') else 'N/A'}")
            return {"error": True, "status_code": response.status_code if hasattr(response, 'status_code') else None, "message": "Falha ao decodificar a resposta da API Omie"}
        except Exception as e:
            print(f"Erro inesperado ao chamar API Omie: {e}")
            return {"error": True, "status_code": None, "message": "Erro inesperado no processamento da API"}


# --- The Main Tool ---
@mcp.tool()
async def encontrar_pedidos_cliente(
    cnpj_cpf: Optional[str] = Field(None, description="CNPJ ou CPF do cliente."),
    nome_fantasia: Optional[str] = Field(None, description="Nome fantasia do cliente."),
    cidade: Optional[str] = Field(None, description="Cidade do cliente.")
    # Optional: Adicionar parâmetro Context se precisar de logging avançado: ctx: Context
) -> List[Dict[str, Any]] | str:
    """
    Encontra um cliente utilizando CNPJ/CPF, Nome Fantasia ou Cidade, e então busca
    e retorna detalhes sobre seus últimos 3 pedidos de venda da API Omie.
    Requer pelo menos um parâmetro de busca (cnpj_cpf, nome_fantasia, ou cidade).
    Retorna uma lista de detalhes dos pedidos ou uma mensagem de erro em string.
    """
    # 1. --- Validação da Entrada ---
    if not any([cnpj_cpf, nome_fantasia, cidade]):
        return "Erro: Forneça ao menos um parâmetro de busca (CNPJ/CPF, Nome Fantasia, ou Cidade)."
    print(f"Buscando cliente com: CNPJ/CPF='{cnpj_cpf}', Nome Fantasia='{nome_fantasia}', Cidade='{cidade}'")

    # Normaliza o CNPJ/CPF de entrada uma vez
    normalized_input_cnpj_cpf = ''.join(filter(str.isdigit, cnpj_cpf)) if cnpj_cpf else None

    # 2. --- Encontrar ID do Cliente (Chamar ListarClientes com Paginação) ---
    print("Buscando ID do cliente (com paginação)...")
    
    current_page = 1
    total_pages = 1 # Será atualizado após a primeira chamada
    customer_id = None
    found_customer_details = None
    possible_matches_by_name = [] # Para lidar com múltiplos nomes fantasia

    while current_page <= total_pages:
        if customer_id: # Se já encontramos por CNPJ, não precisa continuar paginando
            break

        print(f"Consultando API Omie - ListarClientes - Página {current_page} de {total_pages if total_pages > 1 else 'desconhecido ainda'}")
        
        # Monta o filtro base. Se o CNPJ foi fornecido, ele é o filtro principal.
        # Se não, nome_fantasia ou cidade podem ser usados, mas com mais cuidado para múltiplos.
        cliente_filter = {}
        if normalized_input_cnpj_cpf:
            cliente_filter["cnpj_cpf"] = normalized_input_cnpj_cpf
        elif nome_fantasia: # Só usa nome_fantasia no filtro se CNPJ não foi dado
            cliente_filter["nome_fantasia"] = nome_fantasia
        elif cidade: # Só usa cidade no filtro se CNPJ e Nome Fantasia não foram dados
            cliente_filter["cidade"] = cidade
        
        # Se nenhum filtro primário (CNPJ, Nome, Cidade) foi usado diretamente na API
        # porque estamos paginando para encontrar um CNPJ/Nome específico,
        # precisamos de um filtro base para a API não reclamar, ou ajustar a lógica.
        # Por enquanto, a API Omie parece aceitar um filtro vazio e paginar tudo,
        # mas isso pode ser ineficiente.
        # A abordagem mais eficiente é filtrar o máximo possível na API.

        listar_clientes_params = [{
            "pagina": current_page,
            "registros_por_pagina": 50,
            "apenas_importado_api": "N",
            "clientesFiltro": cliente_filter if any(cliente_filter) else {} # Envia filtro se houver, ou vazio.
        }]

        cliente_response = await call_omie_api("/geral/clientes/", "ListarClientes", listar_clientes_params)

        if cliente_response.get("error"):
            return f"Erro ao buscar cliente (página {current_page}): {cliente_response.get('message', 'Erro desconhecido na API')}"

        if current_page == 1: # Na primeira resposta, pegamos o total de páginas
            total_pages = cliente_response.get("total_de_paginas", 1)
            print(f"Total de páginas detectado: {total_pages}")

        clientes_cadastro_pagina_atual = cliente_response.get("clientes_cadastro")

        if clientes_cadastro_pagina_atual:
            for cliente_in_list in clientes_cadastro_pagina_atual:
                api_cnpj_cpf = ''.join(filter(str.isdigit, cliente_in_list.get("cnpj_cpf", "")))
                api_nome_fantasia = cliente_in_list.get("nome_fantasia", "")

                if normalized_input_cnpj_cpf and api_cnpj_cpf == normalized_input_cnpj_cpf:
                    if found_customer_details: # Já tinha achado um, agora outro com mesmo CNPJ? Improvável, mas...
                        return f"Erro: Múltiplos registros encontrados com o mesmo CNPJ/CPF ({cnpj_cpf}) na paginação. Verifique os dados na Omie."
                    print(f"Cliente encontrado por CNPJ/CPF na página {current_page}.")
                    found_customer_details = cliente_in_list
                    customer_id = cliente_in_list.get("codigo_cliente_omie")
                    break # Encontrou por CNPJ, sai do loop de clientes da página
                
                elif nome_fantasia and not normalized_input_cnpj_cpf and nome_fantasia.lower() in api_nome_fantasia.lower():
                    # Se buscando por nome_fantasia, coletamos todos os matches
                    possible_matches_by_name.append(cliente_in_list)
            
            if customer_id: # Se encontrou por CNPJ nesta página
                break # Sai do loop de paginação (while)
        
        if not clientes_cadastro_pagina_atual and current_page == 1 and total_pages == 1:
            # Nenhum cliente encontrado na primeira e única página com os filtros diretos.
            return "Erro: Cliente não encontrado com os critérios fornecidos (nenhum resultado na primeira página)."

        current_page += 1
        if current_page > total_pages and not customer_id and not possible_matches_by_name:
             print("Todas as páginas verificadas, nenhum cliente encontrado.")


    # Após o loop de paginação, processar os resultados da busca por nome_fantasia se aplicável
    if not customer_id and possible_matches_by_name:
        if len(possible_matches_by_name) == 1:
            print("Cliente encontrado por Nome Fantasia após paginação.")
            found_customer_details = possible_matches_by_name[0]
            customer_id = found_customer_details.get("codigo_cliente_omie")
        elif len(possible_matches_by_name) > 1:
            # Poderíamos listar os nomes aqui para o usuário, mas a ferramenta MCP atual não tem interação.
            unique_names = {match.get("nome_fantasia"): match for match in possible_matches_by_name}
            if len(unique_names) == 1: # Múltiplos registros com o mesmo nome fantasia exato
                print("Múltiplos registros com o mesmo Nome Fantasia exato encontrado após paginação. Usando o primeiro.")
                found_customer_details = list(unique_names.values())[0]
                customer_id = found_customer_details.get("codigo_cliente_omie")
            else:
                return f"Erro: Múltiplos clientes ({len(unique_names)}) encontrados com o Nome Fantasia '{nome_fantasia}' após verificar todas as páginas. Por favor, forneça um CNPJ/CPF ou um Nome Fantasia mais específico."
    
    # 3. --- Validar se o cliente foi encontrado ---
    if not customer_id or not found_customer_details:
        return "Erro: Cliente não encontrado com os critérios fornecidos após verificar todas as páginas."

    print(f"Detalhes do cliente encontrado: {found_customer_details.get('nome_fantasia')} - ID: {customer_id} (Tipo: {type(customer_id)})")

    # 4. --- Encontrar Pedidos (Chamar ListarPedidos) ---
    print(f"Buscando pedidos para o cliente ID: {customer_id}...") # Log existente, útil
    listar_pedidos_params = [{
        "pagina": 1,
        "registros_por_pagina": 50, # Ajustado para 50 para ser conservador, pode aumentar se necessário
        "apenas_importado_api": "N",
        "filtrar_por_cliente": customer_id 
    }]

    # O endpoint para ListarPedidos é /produtos/pedido/
    pedidos_response = await call_omie_api("/produtos/pedido/", "ListarPedidos", listar_pedidos_params)

    # --- Tratar Resposta do ListarPedidos ---
    if pedidos_response.get("error"):
        return f"Erro ao buscar pedidos: {pedidos_response.get('message', 'Erro desconhecido na API')}"
    
    pedidos_venda_produto = pedidos_response.get("pedido_venda_produto")

    if not pedidos_venda_produto:
        # Modificar a mensagem de erro para ser mais informativa
        return f"Nenhum pedido encontrado para o cliente ID: {customer_id} na página 1. O cliente pode não ter pedidos ou o ID pode ter algum problema."

    # 5. --- Processar Pedidos ---
    print("Processando pedidos...")
    # A API Omie não garante a ordem. Para pegar os "últimos", precisaríamos de um campo de data para ordenar.
    # Assumindo, por agora, que os primeiros são os mais relevantes ou recentes se a API os retornar assim.
    # Se precisar ordenar por data (ex: data_previsao, ou infoCadastro.dInc), 
    # seria necessário buscar mais pedidos e implementar a lógica de ordenação aqui.
    # Por simplicidade, pegaremos os primeiros 3 da lista retornada.
    
    # Ordenar por 'numero_pedido' decrescente como uma heurística para "mais recentes" se data não for fácil
    # Ou, se houver um campo de data confiável no cabeçalho, usá-lo.
    # Exemplo de ordenação por numero_pedido (tratar como string pode não ser ideal para números grandes)
    try:
        pedidos_ordenados = sorted(
            pedidos_venda_produto, 
            key=lambda p: p.get("cabecalho", {}).get("numero_pedido", "0"), 
            reverse=True
        )
    except Exception as e:
        print(f"Não foi possível ordenar os pedidos por numero_pedido: {e}. Usando a ordem da API.")
        pedidos_ordenados = pedidos_venda_produto

    recent_orders = pedidos_ordenados[:3]

    # 6. --- Formatar Saída ---
    print(f"Formatando os {len(recent_orders)} pedidos mais recentes...")
    formatted_orders = []
    for order in recent_orders:
        cabecalho = order.get("cabecalho", {})
        total_pedido_info = order.get("total_pedido", {})
        itens_list = []
        for item_detail in order.get("det", []):
            produto_info = item_detail.get("produto", {})
            itens_list.append({
                "descricao_produto": produto_info.get("descricao", "N/A"),
                "quantidade": produto_info.get("quantidade", 0),
                "valor_unitario": produto_info.get("valor_unitario", 0.0),
                "valor_total_item": produto_info.get("valor_total", 0.0) 
            })

        formatted_orders.append({
            "numero_pedido": cabecalho.get("numero_pedido", "N/A"),
            "data_previsao": cabecalho.get("data_previsao", "N/A"),
            "etapa_pedido": cabecalho.get("etapa", "N/A"), # Etapa pode ser útil
            "valor_total_pedido": total_pedido_info.get("valor_total_pedido", 0.0),
            "itens": itens_list
        })

    print(f"Pedidos formatados: {len(formatted_orders)}")
    if not formatted_orders:
        return f"Nenhum pedido processado para o cliente ID: {customer_id}. A lista de pedidos pode estar vazia ou em um formato inesperado."
        
    return formatted_orders

# --- Standard Run Block ---
if __name__ == "__main__":
    print("Iniciando Servidor de Integração Omie MCP...")
    # Isso executa o servidor usando o transporte stdio padrão
    # Acessível por clientes como o Claude Desktop ou scripts personalizados
    # Para testar com `fastmcp dev server.py` ou `fastmcp run server.py`
    mcp.run() 