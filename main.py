import asyncio
from padex import main as run_server

def main():
    """Launch the Paloma DEX MCP Server"""
    print("Starting Paloma DEX MCP Server...")
    asyncio.run(run_server())

if __name__ == "__main__":
    main()
