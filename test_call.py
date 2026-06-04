from agent_framework import MCPStdioTool
import asyncio

async def test():
    m = MCPStdioTool(name='test', command='python', args=['finance_server.py'])
    await m.connect()
    await m.load_tools()
    
    # Try calling the tool directly
    result = await m.call_tool('get_stock_quote', {'ticker': 'AAPL'})
    print("Result type:", type(result))
    print("Result:", result)
    
    await m.close()

asyncio.run(test())
