"""
Finance Research Agent — Azure OpenAI + MCP
--------------------------------------------
Uses the openai SDK directly with Azure endpoint,
since agent_framework.azure in this version is the
Microsoft Durable Agents SDK (not a chat client).

Usage:
    python main.py
    python main.py --mode demo
    python main.py --mode single --query "Get me a quote for TSLA"
"""

import asyncio
import argparse
import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from agent_framework import MCPStdioTool

load_dotenv(".env")

# ─── Config ────────────────────────────────────────────────────────────────────

ENDPOINT    = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY     = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT  = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

MCP_SERVER_SCRIPT = os.path.join(
    os.path.dirname(__file__), "finance_server.py"
)

SYSTEM_PROMPT = """
You are FinanceGPT, an expert AI financial research assistant powered by real-time tools.

YOUR CAPABILITIES (via MCP tools):
• Real-time stock quotes and multi-stock comparisons
• Portfolio analysis and concentration checks
• Compound interest and investment growth projections
• Loan/mortgage payment calculations with amortization
• Retirement readiness assessment using the 4% rule
• Monthly budget analysis using the 50/30/20 framework
• DCF (Discounted Cash Flow) stock valuation models

YOUR APPROACH:
1. Always use the appropriate MCP tool when performing calculations.
2. Present numbers clearly with dollar signs and percentages.
3. Explain what the numbers mean in plain English after showing them.
4. Highlight risks, assumptions, and limitations in your analysis.
5. Never give personalized investment advice — frame insights as educational analysis.

IMPORTANT DISCLAIMER: This is for educational and research purposes only.
Always recommend consulting a licensed financial advisor for personalized advice.
""".strip()

DEMO_QUERIES = [
    "Get me a stock quote for NVDA and explain what the numbers mean.",
    "Compare AAPL, MSFT, and GOOGL stocks side by side.",
    "I'm 32 years old with $45,000 saved, contributing $800/month. I want to retire at 65 with $6,000/month income. Am I on track?",
    "Calculate compound interest: $10,000 invested for 20 years at 8% with $300/month contributions.",
    "I want to buy a $380,000 home with 20% down at 6.8% for 30 years. What's my monthly payment? What if I pay $200 extra/month?",
    "Analyze my budget: income $7,500/month. Expenses: rent $1,800, groceries $450, car_payment $380, insurance $120, utilities $150, dining $320, netflix $20, gym $45, shopping $200.",
]


# ─── Agent Runner ───────────────────────────────────────────────────────────────

async def run_agent_session(mode: str = "interactive", single_query: str = None):
    _print_banner()

    if mode != "demo":
        input("\nPress Enter to start the Finance MCP server...")

    print("\n⚙️  Starting Finance MCP server...")

    try:
        async with MCPStdioTool(
            name="finance-research",
            command="python",
            args=[MCP_SERVER_SCRIPT],
        ) as mcp_server:

            print("✅ Finance MCP server started\n")

            # Build tools list from MCP server
            tools = await _build_tools(mcp_server)
            print(f"✅ Loaded {len(tools)} MCP tools\n")

            # Create Azure OpenAI client
            client = AzureOpenAI(
                azure_endpoint=ENDPOINT,
                api_key=API_KEY,
                api_version=API_VERSION,
            )

            print("✅ FinanceGPT agent ready\n")
            print("-" * 75)

            if mode == "demo":
                await _run_demo(client, tools, mcp_server)
            elif mode == "single":
                if not single_query:
                    print("❌ --query is required with --mode single")
                    return
                await _ask(client, tools, mcp_server, single_query)
            else:
                await _run_interactive(client, tools, mcp_server)

    except FileNotFoundError as e:
        print(f"\n❌ Could not find MCP server script: {e}")
        print(f"   Looking for: {MCP_SERVER_SCRIPT}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


async def _build_tools(mcp_server) -> list:
    """Convert MCP tools to OpenAI function calling format."""
    tools = []
    try:
        await mcp_server.load_tools()
        mcp_tools = mcp_server.functions
        for tool in mcp_tools:
            schema = getattr(tool, '_input_schema_cached', None) or {"type": "object", "properties": {}}
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": schema,
                }
            })
    except Exception as e:
        print(f"⚠️  Warning: Could not load MCP tools: {e}")
    return tools


async def _call_mcp_tool(mcp_server, tool_name: str, tool_args: dict) -> str:
    """Call an MCP tool by finding it in functions list and invoking it."""
    try:
        # Find the tool by name
        tool = next((f for f in mcp_server.functions if f.name == tool_name), None)
        if not tool:
            return f"Tool '{tool_name}' not found"
        
        # Call the tool directly with kwargs
        result = await tool.invoke(**tool_args)
        return str(result)
    except Exception as e:
        return f"Error calling {tool_name}: {str(e)}"


async def _ask(client, tools, mcp_server, question: str, history: list = None):
    """Send one question, handle tool calls, print response."""
    if history is None:
        history = []

    print(f"\n💭 You: {question}")
    print("\n🤖 FinanceGPT:\n")

    # Build messages: system + full history + new question
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    # Agentic loop - max 5 iterations to prevent infinite loops
    max_iterations = 5
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )

        message = response.choices[0].message

        # No tool calls - final answer
        if not message.tool_calls:
            print(message.content)
            #save to history
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": message.content})
            break

        # Handle tool calls
        messages.append(message)

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"  🔧 Calling tool: {tool_name}")

            result = await _call_mcp_tool(mcp_server, tool_name, tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    print("\n" + "-" * 75)


async def _run_demo(client, tools, mcp_server):
    print("DEMO MODE - Running preset finance queries\n")
    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n[Demo {i}/{len(DEMO_QUERIES)}]")
        await _ask(client, tools, mcp_server, query)
        if i < len(DEMO_QUERIES):
            input("\nPress Enter for next demo query...")


async def _run_interactive(client, tools, mcp_server):
    print("INTERACTIVE MODE - Type your finance questions")
    print("   Commands: 'demo' to run demos | 'clear' to reset memory | 'quit' to exit\n")
    _print_example_queries()

    # Persistent conversation history
    history = []

    while True:
        try:
            user_input = input("\n💭 You: ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("\n✅ Goodbye! Remember: always consult a financial advisor.")
                break
            if user_input.lower() == "demo":
                await _run_demo(client, tools, mcp_server)
                continue
            if user_input.lower() == "help":
                _print_example_queries()
                continue
            if user_input.lower() == "clear":
                history = []
                print("🧹 Memory cleared — starting fresh.")
                continue

            await _ask(client, tools, mcp_server, user_input, history)

        except KeyboardInterrupt:
            print("\n\nSession ended.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


# ─── UI Helpers ──────────────────────────────────────────────────────────────

def _print_banner():
    print("\n" + "=" * 75)
    print("  💰  FINANCE RESEARCH AGENT  |  Azure OpenAI + MCP")
    print("=" * 75)
    print(f"""
  Model:      {DEPLOYMENT}
  Endpoint:   {ENDPOINT or 'Not set - check your .env'}
  MCP Server: finance_server.py

  Tools:
  📈 Stock quotes & comparisons     🏦 Loan & mortgage calculator
  💼 Portfolio analyzer             🧮 Compound interest projector
  📊 DCF valuation model            👴 Retirement readiness check
  💸 Budget analyzer (50/30/20)
    """)


def _print_example_queries():
    print("""
  Example questions:
  ──────────────────────────────────────────────────────────────
  • "Get me a stock quote for TSLA"
  • "Compare AAPL, MSFT, and AMZN"
  • "I'm 35 with $80k saved, retiring at 65. Am I on track for $7k/month?"
  • "Monthly payment on a $500k mortgage at 7% for 30 years?"
  • "Invest $5,000 at 8% for 30 years with $500/month contributions"
  • "Analyze my budget: income $8000, rent $2000, groceries $500, car $400"
  ──────────────────────────────────────────────────────────────
    """)


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance Research Agent")
    parser.add_argument(
        "--mode",
        choices=["interactive", "demo", "single"],
        default="interactive",
    )
    parser.add_argument("--query", type=str)
    args = parser.parse_args()

    asyncio.run(run_agent_session(mode=args.mode, single_query=args.query))