# Projeto de Integração Omie com IA

## Visão Geral

Este projeto demonstra uma integração com a API Omie para buscar informações de clientes e seus pedidos, utilizando um servidor backend construído com FastMCP. Adicionalmente, inclui uma ferramenta experimental que utiliza a IA Generativa do Google (Gemini) para responder perguntas em linguagem natural sobre os pedidos dos clientes.

## Funcionalidades Principais

O backend expõe as seguintes ferramentas principais:

1.  `encontrar_pedidos_cliente`:
    *   Busca um cliente na API Omie utilizando CNPJ/CPF, Nome Fantasia ou Cidade.
    *   Retorna detalhes dos últimos 3 pedidos de venda do cliente encontrado.

2.  `responder_pergunta_sobre_pedidos`:
    *   Recebe uma pergunta do usuário em linguagem natural sobre pedidos de um cliente.
    *   Utiliza IA (Google Gemini) para interpretar a pergunta, extrair dados do cliente (CNPJ/CPF, Nome Fantasia, Cidade).
    *   Chama a ferramenta `encontrar_pedidos_cliente` para buscar os dados dos pedidos.
    *   Utiliza IA novamente para formular uma resposta em linguagem natural com base nos dados dos pedidos e na pergunta original.

## Estrutura do Projeto

```
.
├── backend/
│   ├── server.py             # Lógica principal do servidor FastMCP, ferramentas e integração com APIs.
│   ├── client_test.py        # Script para testar as ferramentas do servidor.
│   ├── config.py             # Carregamento de configurações (chaves de API, etc.).
│   ├── requirements.txt      # Dependências Python do projeto.
│   ├── pyproject.toml        # Configurações do projeto Python (ex: para Poetry ou Hatch).
│   └── .env.example          # Arquivo de exemplo para variáveis de ambiente (NÃO FAÇA COMMIT DO SEU .env!).
└── README.md                 # Este arquivo.
```

## Configuração do Ambiente

Siga os passos abaixo para configurar e executar o projeto.

### 1. Pré-requisitos

*   Python 3.8 ou superior.
*   Acesso à internet para baixar dependências e interagir com as APIs.

### 2. Instalação de Dependências

Clone o repositório (se ainda não o fez) e navegue até a pasta raiz do projeto.
Crie e ative um ambiente virtual (recomendado):

```bash
python -m venv venv
# No Windows
venv\Scripts\activate
# No macOS/Linux
source venv/bin/activate
```

Instale as dependências listadas no arquivo `requirements.txt` que está dentro da pasta `backend`:

```bash
pip install -r backend/requirements.txt
```

### 3. Configuração das Variáveis de Ambiente

Este projeto requer chaves de API para interagir com a Omie e com o Google Gemini.

1.  Na pasta `backend`, crie um arquivo chamado `.env` (você pode copiar o `backend/.env.example` se ele existir, ou criar um novo).
2.  Adicione as seguintes variáveis ao seu arquivo `backend/.env`, substituindo os valores de exemplo pelas suas credenciais reais:

    ```env
    OMIE_APP_KEY="SUA_APP_KEY_OMIE"
    OMIE_APP_SECRET="SUA_APP_SECRET_OMIE"
    GOOGLE_API_KEY="SUA_GOOGLE_API_KEY"
    ```

    *   `OMIE_APP_KEY` e `OMIE_APP_SECRET`: Suas credenciais para a API Omie.
    *   `GOOGLE_API_KEY`: Sua chave de API para os serviços do Google Generative AI (Gemini).

    **IMPORTANTE**: Nunca adicione o arquivo `.env` contendo suas chaves secretas ao controle de versão (Git). O arquivo `.gitignore` já deve estar configurado para ignorá-lo, mas verifique.

## Como Usar

### 1. Iniciando o Servidor

Para iniciar o servidor FastMCP, navegue até a pasta `backend` no seu terminal e execute o `server.py`:

```bash
cd backend
python server.py
```

Por padrão, o `server.py` está configurado para executar um teste direto da ferramenta de IA (`main_test_ia()`) ao invés de iniciar o servidor MCP completo. Para iniciar o servidor MCP para ser acessado pelo `client_test.py`, você precisará comentar a chamada `asyncio.run(main_test_ia())` e descomentar `mcp.run()` no final do arquivo `server.py`:

```python
# server.py (final do arquivo)

# ... (código anterior)

if __name__ == "__main__":
    print("Iniciando Servidor de Integração Omie MCP...")
    mcp.run() # DESCOMENTE ESTA LINHA para rodar o servidor MCP

    # Teste direto da função de IA
    # async def main_test_ia():
    #     # ... (código de teste)
    # asyncio.run(main_test_ia()) # COMENTE ESTA LINHA para rodar o servidor MCP
```

Após a modificação, execute `python server.py` novamente. O servidor estará em execução e pronto para receber chamadas.

### 2. Executando o Cliente de Teste

O script `client_test.py` (localizado na pasta `backend`) pode ser usado para interagir com as ferramentas expostas pelo servidor.

Com o servidor (`server.py`) em execução (e configurado para rodar o `mcp.run()`), abra um **novo terminal**, navegue até a pasta `backend` e execute:

```bash
cd backend
python server.py
```

O cliente tentará se conectar ao servidor, listar as ferramentas disponíveis e chamar a ferramenta `responder_pergunta_sobre_pedidos` com uma pergunta de exemplo.

## Tecnologias Utilizadas

*   **Python**: Linguagem de programação principal.
*   **FastMCP**: Framework para criação rápida de microsserviços e ferramentas.
*   **Httpx**: Cliente HTTP assíncrono para chamadas à API Omie.
*   **Pydantic**: Para validação de dados e gerenciamento de configurações.
*   **Google Generative AI (Gemini)**: Modelo de IA para processamento de linguagem natural.
*   **API Omie**: ERP online para gestão empresarial, de onde os dados de clientes e pedidos são consumidos.

## Possíveis Melhorias e Considerações

*   **Tratamento de Erros**: Aprimorar o tratamento de erros e logging em todas as camadas.
*   **Segurança**: Revisar e implementar melhores práticas de segurança, especialmente no manuseio de chaves de API.
*   **Paginação Completa na IA**: A ferramenta de IA atualmente busca os últimos 3 pedidos. Para perguntas mais complexas que exijam análise de um histórico maior, seria necessário implementar uma busca e processamento de todos os pedidos do cliente.
*   **Testes Unitários e de Integração**: Adicionar testes automatizados para garantir a robustez do código.
*   **Interface de Usuário**: Para uma utilização mais amigável, poderia ser desenvolvida uma interface gráfica ou web.

--

#Para mudar o prompt basta acessar o codigo `server.py`

```python
# server.py (final do arquivo)

# ... (código anterior)

if __name__ == "__main__":
    print("Iniciando Servidor de Integração Omie MCP...")
    mcp.run() # DESCOMENTE ESTA LINHA para rodar o servidor MCP

    async def main_test_ia():
        print("--- INICIANDO TESTE DIRETO DA FERRAMENTA DE IA ---")
        pergunta_teste = "desreve destalhamente o ultimo pedido do cliente com o CNPJ 359.489.811-34?" #ALTERE AQUI!!!!
        print(f"Pergunta de teste: {pergunta_teste}")
```

