# 💰 Finance Research Agent

> **Azure AI Foundry + MCP** — An intelligent financial research assistant with real-time market data, portfolio analysis, and financial calculators.  
> Built for resume demonstration of agentic AI systems using Microsoft's Azure AI Foundry framework.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│          User Interface                     │
│   CLI (main.py)  │  Streamlit (app.py)      │
└────────────┬────────────────────────────────┘
             │
┌────────────▼────────────────────────────────┐
│     Azure AI Foundry Agent (GPT-4o)         │
│  agent_framework.azure.AzureOpenAIChatClient│
└────────────┬────────────────────────────────┘
             │ MCPStdioTool
┌────────────▼────────────────────────────────┐
│        Finance MCP Server                   │
│         (finance_server.py)                 │
├────────────────────────────────────────────┤
│  📈 Stock Quotes   │  🧮 Calculators        │
│  ⚖️ Comparisons    │  👴 Retirement         │
│  💼 Portfolio      │  💸 Budget Analyzer    │
│  📊 DCF Valuation  │                        │
└─────────────────────┬──────────────────────┘
                      │
         ┌────────────▼───────────┐
         │   Yahoo Finance API    │
         │   (real-time quotes)   │
         └────────────────────────┘
```

## 🔧 MCP Tools

| Tool | Description |
|------|-------------|
| `get_stock_quote` | Real-time price, volume, 52w high/low |
| `compare_stocks` | Side-by-side multi-stock comparison |
| `analyze_portfolio` | Allocation weights, concentration risk |
| `calculate_compound_interest` | Investment growth with contributions |
| `calculate_loan_payment` | Monthly payment + extra payment savings |
| `calculate_retirement_readiness` | Gap analysis using 4% withdrawal rule |
| `analyze_budget` | 50/30/20 framework + recommendations |
| `calculate_dcf_valuation` | Intrinsic value via discounted cash flows |

## 🚀 Setup

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# 3. Run CLI agent
python agent/main.py

# Run in demo mode (preset queries)
python agent/main.py --mode demo

# Run single query
python agent/main.py --mode single --query "Get me a quote for TSLA"

# 4. Run Streamlit UI (optional)
streamlit run streamlit_app/app.py
```

## 💬 Example Interactions

```
You: Compare AAPL, MSFT, and NVDA

You: I'm 34 years old with $50k saved, contributing $600/month.
     I want to retire at 67 with $7,000/month income. Am I on track?

You: Mortgage calc: $400k home, 20% down, 7.1% for 30 years.
     What if I pay $500 extra/month?

You: Analyze my budget: income $8500, rent $2000, groceries $600,
     car_payment $450, dining $400, netflix $18, gym $60, shopping $300

You: Run a DCF on a company with $5B FCF, 20% growth, 10% discount rate
```

## 📁 Project Structure

```
finance-agent-mcp/
├── agent/
│   └── main.py              # CLI agent entry point
├── mcp_server/
│   └── finance_server.py    # Custom MCP server with 8 finance tools
├── streamlit_app/
│   └── app.py               # Optional Streamlit chat UI
├── .env.example             # Credential template
├── requirements.txt
└── README.md
```

## 🎯 Resume Talking Points

- **Agentic AI**: Built a multi-tool agent using **Microsoft Azure AI Foundry** agent framework
- **MCP Protocol**: Designed and implemented a custom **Model Context Protocol (MCP)** server exposing domain-specific financial tools
- **Real-time Data**: Integrated live market data via async HTTP (Yahoo Finance API)
- **Financial Modeling**: Implemented DCF valuation, compound interest, loan amortization, and retirement planning models
- **Full-stack**: Optional **Streamlit** UI with chat history, tool call transparency, and quick-start prompts
- **Tool Orchestration**: Agent autonomously selects and chains MCP tools based on user intent

## ⚠️ Disclaimer

This application is for **educational and demonstration purposes only**. It does not constitute financial advice. Always consult a licensed financial advisor for personal investment decisions.
