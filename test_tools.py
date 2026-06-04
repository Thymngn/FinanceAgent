from agent_framework import MCPStdioTool
import asyncio

async def test():
    m = MCPStdioTool(name='test', command='python', args=['finance_server.py'])
    await m.connect()
    await m.load_tools()
    f = m.functions[0]
    print("DIR:", dir(f))
    print("VARS:", vars(f))
    await m.close()

asyncio.run(test())
