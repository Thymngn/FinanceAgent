"""
Finance Research Agent — Streamlit UI
--------------------------------------
Run with: streamlit run app.py
"""

import asyncio
import os
import json
from datetime import datetime

import streamlit as st
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
    os.path.dirname(os.path.abspath(__file__)), "finance_server.py"
)

SYSTEM_PROMPT = """
You are FinanceGPT, an expert AI financial research assistant powered by real-time tools.
Use your MCP tools for all calculations and data retrieval.
Present results clearly with context and plain-English explanations.
Flag risks and assumptions. Frame everything as educational analysis, not personalized advice.
""".strip()

STARTER_PROMPTS = [
    ("📈 Stock Quote", "Get me a real-time quote for NVDA and explain what the numbers mean"),
    ("⚖️ Compare Stocks", "Compare AAPL, MSFT, and GOOGL side by side"),
    ("👴 Retirement Check", "I'm 35 with $60k saved, contributing $700/month. Retire at 65 with $6k/month income. Am I on track?"),
    ("🏠 Mortgage Calc", "Monthly payment on a $450k home, 20% down, 6.9% rate, 30 years. What if I pay $300 extra/month?"),
    ("📊 Budget Review", "Analyze my budget: income $7000. rent $1600, groceries $500, car_payment $350, dining $300, netflix $20, gym $50"),
    ("💹 Compound Growth", "If I invest $15,000 today at 8% for 25 years with $500/month, what will I have?"),
]


# ─── Page Setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Research Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color: #0f1117; }
.user-msg {
    background: #1e2530;
    border-left: 3px solid #00d4aa;
    padding: 12px 16px;
    border-radius: 4px;
    margin: 8px 0;
    color: #e8eaf0;
}
.agent-msg {
    background: #161b27;
    border-left: 3px solid #4f8ef7;
    padding: 12px 16px;
    border-radius: 4px;
    margin: 8px 0;
    color: #e8eaf0;
}
.tool-badge {
    display: inline-block;
    background: #1a2332;
    border: 1px solid #2d4060;
    color: #7bb3f0;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 12px;
    margin: 2px;
    font-family: monospace;
}
</style>
""", unsafe_allow_html=True)


# ─── Session State ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []  # conversation memory
if "tool_calls_total" not in st.session_state:
    st.session_state.tool_calls_total = 0


# ─── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 Finance Agent")
    st.caption("Azure OpenAI + MCP")
    st.divider()

    connected = bool(ENDPOINT and API_KEY)
    st.markdown(f"{'🟢' if connected else '🔴'} **Azure OpenAI** {'Connected' if connected else 'Check .env'}")
    st.markdown(f"📡 **Model:** `{DEPLOYMENT}`")
    st.markdown(f"🔧 **MCP:** finance_server.py")
    st.divider()

    st.markdown("### ⚡ Quick Queries")
    for label, prompt in STARTER_PROMPTS:
        if st.button(label, use_container_width=True):
            st.session_state.pending_prompt = prompt
            st.rerun()

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.history = []
            st.session_state.tool_calls_total = 0
            st.rerun()
    with col2:
        if st.button("🧹 Clear Memory", use_container_width=True):
            st.session_state.history = []
            st.info("Memory cleared")
            st.rerun()

    st.divider()

    with st.expander("🔧 Available MCP Tools"):
        tools_list = {
            "get_stock_quote": "Real-time stock price",
            "compare_stocks": "Multi-stock comparison",
            "analyze_portfolio": "Portfolio allocation",
            "calculate_compound_interest": "Investment growth",
            "calculate_loan_payment": "Loan amortization",
            "calculate_retirement_readiness": "Retirement gap",
            "analyze_budget": "50/30/20 budget review",
            "calculate_dcf_valuation": "DCF stock valuation",
        }
        for tool, desc in tools_list.items():
            st.markdown(f"`{tool}`  \n{desc}")

    st.markdown("""
    <div style='background:#1a1520;border:1px solid #3d2b40;border-radius:6px;
    padding:10px;font-size:11px;color:#9980a0;margin-top:8px;'>
    ⚠️ Educational purposes only. Not financial advice.
    </div>
    """, unsafe_allow_html=True)


# ─── Main UI ───────────────────────────────────────────────────────────────────

st.markdown("""
<h1 style='text-align:center;color:#e8eaf0;font-weight:700;margin-bottom:0;'>
    💰 Finance Research Agent
</h1>
<p style='text-align:center;color:#6b7899;margin-top:4px;'>
    Azure OpenAI · GPT-4o-mini · MCP Tools · Real-time Data
</p>
""", unsafe_allow_html=True)

st.divider()

# Stats
c1, c2, c3, c4 = st.columns(4)
c1.metric("Messages", len(st.session_state.messages))
c2.metric("Tool Calls", st.session_state.tool_calls_total)
c3.metric("Memory", f"{len(st.session_state.history)//2} turns")
c4.metric("Model", DEPLOYMENT)

st.divider()

# Empty state
if not st.session_state.messages:
    st.markdown("""
    <div style='text-align:center;padding:40px 0;color:#6b7899;'>
        <div style='font-size:48px;margin-bottom:12px;'>📊</div>
        <div style='font-size:18px;font-weight:600;color:#9ba8c0;'>
            Ask me anything about stocks, budgets, retirement, or investments
        </div>
        <div style='font-size:13px;margin-top:8px;'>
            Use the quick queries in the sidebar to get started
        </div>
    </div>
    """, unsafe_allow_html=True)

# Render chat messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class='user-msg'>
            <strong style='color:#00d4aa;'>You</strong>
            <span style='float:right;font-size:11px;color:#4a5568;'>{msg.get('time','')}</span>
            <div style='margin-top:6px;'>{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        tools_used = msg.get("tools_used", [])
        tools_html = "".join(f"<span class='tool-badge'>🔧 {t}</span>" for t in tools_used)
        st.markdown(f"""
        <div class='agent-msg'>
            <strong style='color:#4f8ef7;'>FinanceGPT</strong>
            <span style='float:right;font-size:11px;color:#4a5568;'>{msg.get('time','')}</span>
            {f"<div style='margin-top:4px;'>{tools_html}</div>" if tools_html else ""}
            <div style='margin-top:6px;white-space:pre-wrap;'>{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)


# ─── Agent Logic ───────────────────────────────────────────────────────────────

async def build_tools(mcp_server) -> list:
    tools = []
    try:
        await mcp_server.load_tools()
        for tool in mcp_server.functions:
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
        st.warning(f"Could not load MCP tools: {e}")
    return tools


async def call_mcp_tool(mcp_server, tool_name: str, tool_args: dict) -> str:
    try:
        tool = next((f for f in mcp_server.functions if f.name == tool_name), None)
        if not tool:
            return f"Tool '{tool_name}' not found"
        result = await tool.invoke(**tool_args)
        return str(result)
    except Exception as e:
        return f"Error calling {tool_name}: {str(e)}"


async def run_agent(user_input: str, history: list) -> tuple[str, list]:
    """Run agent and return (response, tools_used)."""
    async with MCPStdioTool(
        name="finance-research",
        command="python",
        args=[MCP_SERVER_SCRIPT],
    ) as mcp_server:

        tools = await build_tools(mcp_server)

        client = AzureOpenAI(
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
            api_version=API_VERSION,
        )

        # Build messages with memory
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        tools_used = []

        while True:
            response = client.chat.completions.create(
                model=DEPLOYMENT,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content, tools_used

            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tools_used.append(tool_name)

                result = await call_mcp_tool(mcp_server, tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })


def handle_input(user_input: str):
    now = datetime.now().strftime("%H:%M")

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "time": now,
    })

    with st.spinner("🤖 FinanceGPT is analyzing..."):
        try:
            result, tools_used = asyncio.run(
                run_agent(user_input, st.session_state.history)
            )

            # Update memory
            st.session_state.history.append({"role": "user", "content": user_input})
            st.session_state.history.append({"role": "assistant", "content": result})

            # Keep memory to last 10 turns (20 messages) to avoid token limits
            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[-20:]

            st.session_state.tool_calls_total += len(tools_used)
            st.session_state.messages.append({
                "role": "assistant",
                "content": result,
                "tools_used": tools_used,
                "time": datetime.now().strftime("%H:%M"),
            })

        except Exception as e:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ Error: {str(e)}\n\nCheck your .env configuration and MCP server setup.",
                "tools_used": [],
                "time": datetime.now().strftime("%H:%M"),
            })

    st.rerun()


# ─── Input ─────────────────────────────────────────────────────────────────────

user_input = st.chat_input("Ask about stocks, budgets, retirement, investments...")

if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")

if user_input:
    handle_input(user_input)