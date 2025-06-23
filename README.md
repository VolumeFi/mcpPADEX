# Paloma DEX MCP Server

A Model Context Protocol (MCP) server that enables AI agents to interact with Paloma DEX across 7 EVM chains. Built with FastMCP framework for modern MCP implementations.

## Overview

This MCP server provides AI agents with tools to access blockchain data and prepare for decentralized trading operations on Paloma DEX. The server supports cross-chain functionality across Ethereum, Arbitrum, Optimism, Base, BSC, Polygon, and Gnosis chains.

## Features

### Available Tools

- **`get_account_info`**: Get account address and native token balances across all chains
- **`get_pusd_balance`**: Get PUSD token balance on a specific chain
- **`get_chain_info`**: Get detailed information about a specific blockchain
- **`list_supported_chains`**: List all supported chains with their configurations
- **`get_address_balances`**: Get balances for any Ethereum address across all chains

### Chain Support

Supports all 7 EVM chains used by Paloma DEX:
- **Ethereum Mainnet** (Chain ID: 1)
- **Arbitrum One** (Chain ID: 42161)
- **Optimism** (Chain ID: 10)
- **Base** (Chain ID: 8453)
- **BNB Smart Chain** (Chain ID: 56)
- **Polygon** (Chain ID: 137)
- **Gnosis** (Chain ID: 100)

### Key Capabilities

- **Multi-Chain Data Access**: Query balances and chain information across all 7 supported chains
- **FastMCP Framework**: Built with modern MCP implementation for better performance
- **Web3 Integration**: Direct blockchain interaction via Web3 clients
- **Error Handling**: Comprehensive error management and validation
- **Address Validation**: Ethereum address format validation
- **Contract Integration**: Integration with PUSD token contracts

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Cieloc/mcpPADEX.git
   cd mcpPADEX
   ```

2. **Install dependencies** using [uv](https://docs.astral.sh/uv/):
   ```bash
   uv sync
   ```

## Configuration

1. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

2. **Configure your `.env` file** with the following required variables:

   ```bash
   # REQUIRED: Your private key for transaction signing
   # WARNING: Keep this secure and never commit to version control
   PRIVATE_KEY=your_private_key_here

   # Contract addresses for each chain (obtain from Paloma DEX)
   PUSD_TOKEN_ETH=
   PUSD_CONNECTOR_ETH=
   ETF_CONNECTOR_ETH=
   # ... (repeat for all chains)

   # Optional: Moralis API key for enhanced features
   MORALIS_SERVICE_API_KEY=your_moralis_api_key_here
   ```

3. **Obtain contract addresses** from Paloma DEX documentation or team for:
   - PUSD token addresses
   - PUSD connector addresses  
   - ETF connector addresses

## Usage

### Running the Server

```bash
uv run padex.py
```

The server will start and listen for MCP protocol messages via stdin/stdout.

### Tool Examples

#### Get Account Information
```json
{
  "tool": "get_account_info",
  "arguments": {}
}
```

#### Get PUSD Balance
```json
{
  "tool": "get_pusd_balance",
  "arguments": {
    "chain_id": "1"
  }
}
```

#### Get Chain Information
```json
{
  "tool": "get_chain_info",
  "arguments": {
    "chain_id": "42161"
  }
}
```

#### List All Supported Chains
```json
{
  "tool": "list_supported_chains",
  "arguments": {}
}
```

#### Get Address Balances
```json
{
  "tool": "get_address_balances",
  "arguments": {
    "address": "0x742d35Cc6648C4532b6C4EC000e40fd94aea4966"
  }
}
```

## Architecture

### Core Components

- **`padex.py`**: Main MCP server implementation using FastMCP framework
- **`main.py`**: Simple entry point (Hello World)
- **FastMCP Framework**: Modern MCP server implementation with lifecycle management
- **Chain Configuration**: Complete configuration for all 7 supported chains
- **Web3 Clients**: Individual Web3 connections for each blockchain

### Architecture Pattern

The server uses FastMCP's lifespan context management:

```python
@asynccontextmanager
async def paloma_dex_lifespan(server: FastMCP) -> AsyncIterator[PalomaDEXContext]:
    # Initialize Web3 clients and resources
    yield context
    # Cleanup resources
```

### Security Considerations

⚠️ **Important Security Notes**:
- Private keys are stored in environment variables
- Ensure your `.env` file is never committed to version control
- The `.gitignore` file excludes `.env` by default
- Consider using more secure key management for production use

### Dependencies

- **mcp[cli]**: Model Context Protocol with FastMCP framework
- **web3**: Ethereum blockchain interaction
- **eth-account**: Private key and transaction signing
- **eth-abi**: ABI encoding for contract calls
- **httpx**: HTTP client for API interactions
- **python-dotenv**: Environment variable management

## API Integrations

The server integrates with:
- **Blockchain RPC Endpoints**: Direct connection to each supported chain
- **ERC-20 Token Contracts**: For PUSD balance queries
- **Future**: Paloma DEX API integration for trading operations

## Development

### Project Structure
```
mcpPADEX/
├── padex.py                      # Main FastMCP server implementation
├── padex_old.py                  # Previous implementation (backup)
├── main.py                       # Simple entry point
├── pyproject.toml                # Project dependencies
├── .env                          # Environment variables (not committed)
├── .gitignore                    # Git ignore rules
├── MCP_DOCUMENTATION.md          # MCP protocol reference
├── MCP_PYTHON_SDK_REFERENCE.md   # FastMCP SDK reference
├── mcp-llms-full-reference.txt   # Complete MCP reference
└── README.md                     # This file
```

### Adding New Features

The server uses FastMCP decorators for easy extension:

```python
@mcp.tool()
async def new_tool(ctx: Context, param: str) -> str:
    """Tool description"""
    # Implementation
    return result

@mcp.resource("resource://pattern/{id}")
async def new_resource(id: str) -> str:
    """Resource description"""
    # Implementation
    return data
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source. Please check the license file for details.

## Disclaimer

This software is provided "as is" without warranty. Trading cryptocurrencies involves risk of loss. Use at your own risk and ensure you understand the implications of automated trading before deployment.

## Support

For questions about Paloma DEX integration, consult the [Paloma DEX documentation](https://docs.palomachain.com/) or reach out to the Paloma team.

For MCP-related questions, see the [Model Context Protocol documentation](https://modelcontextprotocol.io/).
