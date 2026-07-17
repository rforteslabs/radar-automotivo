# 🚙 Radar Automotivo - Inteligência de Mercado e ETL

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Google Sheets API](https://img.shields.io/badge/Google_Sheets_API-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![ETL Pipeline](https://img.shields.io/badge/Arquitetura-Pipeline_ETL-FF6F00?style=for-the-badge)

## 📌 Sobre o Projeto
Este é um projeto de automação desenvolvido em **Python** focado na coleta de dados de veículos (carros e motos) anunciados em portais da internet. O sistema consome dados via API, filtra as oportunidades mais interessantes baseadas em marcas e características específicas, e armazena tudo de forma estruturada.

Diferente de um simples raspador de tela (scraper), este sistema foi projetado para atuar como uma ferramenta de **Inteligência de Mercado**. Ele gerencia o estado de cada anúncio ao longo do tempo, mapeando flutuações de preços, identificando oportunidades e calculando métricas financeiras cruciais para a decisão de compra.

## ⚙️ Principais Funcionalidades

* **🔄 Rastreamento de Histórico (CDC - Change Data Capture):** O sistema compara os dados da extração atual com a base histórica salva no Google Sheets. Ele sabe identificar se um anúncio é novo, se teve o valor alterado (criando um log da variação) ou se foi removido do portal.
* **⏱️ Tempo de Prateleira (Time to Sell):** Detecta automaticamente quando um anúncio sai do ar e calcula a quantidade de dias que o veículo ficou disponível até a venda.
* **🧮 Enriquecimento de Dados:** Calcula dinamicamente métricas de negócio, como "Custo por KM", "KM Anual Média" e categoriza automaticamente o veículo em faixas de preço.
* **🛡️ Resiliência (Anti-Bloqueio):** Implementação de pausas randômicas (delays) entre as requisições para simular navegação humana e evitar bloqueios por WAF/Firewall na API de origem.
* **📜 Auditoria e Logs:** Sistema profissional de logs configurado para gravar o histórico de execução, processamento e eventuais erros, facilitando o *troubleshooting*.
* **🔐 Gestão de Configurações:** Separação total entre código e configurações. URLs, tempos de pausa e credenciais ficam isolados em um arquivo `config.ini`, seguindo as boas práticas de desenvolvimento (*12-Factor App*).


## 🛠️ Tecnologias Utilizadas
- **Python** (Linguagem principal)
- **Integração de APIs** (Coleta e envio de dados)
- **Google Sheets API** (Banco de dados e armazenamento)
- **Google Looker Studio** (Data Visualization)


## 🏗️ Arquitetura do Pipeline

1. **Extração (Extract):** Consumo paginado da API do portal de veículos, orquestrado a partir de uma lista configurável de marcas.
2. **Transformação (Transform):** Limpeza de dados financeiros, extração de contatos (WhatsApp/Telefone), cálculo de depreciação e cruzamento com a base de dados histórica usando Dicionários e Pandas.
3. **Carga (Load):** Inserção em lote (Bulk) utilizando a biblioteca `gspread_dataframe` para atualizar o Google Sheets, que atua como um banco de dados leve e acessível de qualquer lugar.


## 📊 Dashboard Interativo (Looker Studio)
Para transformar os dados brutos coletados em inteligência de negócio, o projeto conta com uma integração direta com o **Google Looker Studio**. 

Todos os dados extraídos pelo script em Python são alimentados automaticamente em uma planilha do Google Sheets. A partir dessa base, o Dashboard no Looker Studio permite:
- **Filtros Dinâmicos:** Buscar veículos por marca, ano, valor ou outras características desejadas.
- **Análise Visual:** Identificar rapidamente as melhores oportunidades do mercado através de gráficos e tabelas.
- **Acesso Facilitado:** Consultar as informações de forma interativa, sem precisar analisar o código ou planilhas extensas.

### 📸 Visualização do Dashboard
*(Confira abaixo algumas telas do dashboard em funcionamento)*

[Visão Geral do Dashboard Automotivo]

https://github.com/rforteslabs/radar-automotivo/blob/main/dash_veiculos1.png

https://github.com/rforteslabs/radar-automotivo/blob/main/dash_veiculos2.png


## 🚀 Como executar o projeto localmente

### Pré-requisitos
* Python 3.8 ou superior
* Credenciais de Serviço do Google Cloud (`credentials.json`)
* Arquivo de configuração (`config.ini`)
* Arquivo texto com os termos de busca (`marcas.txt`)

### Instalação e Configuração

1. Clone o repositório:
```bash
git clone https://github.com/SEU_USUARIO/radar-automotivo.git
cd radar-automotivo
```
2. Crie e ative o ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows utilize: venv\Scripts\activate
```
3. Instale as dependências:
```bash
pip install -r requirements.txt
```
4. Configure as variáveis do sistema: Crie um arquivo chamado config.ini na pasta raiz do projeto com a seguinte estrutura:
```bash
[API]
BASE_URL = https://url-da-api-aqui.com/endpoint
PAUSA_MIN_PAGINA = 0.5
PAUSA_MAX_PAGINA = 1.5
PAUSA_MIN_MARCA = 2.0
PAUSA_MAX_MARCA = 5.0
NOME_PLANILHA = [nome_planilha]
NOME_ABA = [aba_planilha]
```
5. Crie um arquivo marcas.txt e adicione as marcas que deseja monitorar (uma marca por linha).

6. Execute o sistema:
```bash
python main.py
```

👨‍💻 Autor

Rodrigo Fortes dos Santos

https://www.linkedin.com/in/rodrigofortes

Profissional de Tecnologia com 20 anos de experiência em Infraestrutura/Segurança, em transição para o Desenvolvimento de Software e Engenharia de Dados.
