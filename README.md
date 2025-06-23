# Paloma DEX MCP Server

A Model Context Protocol (MCP) server that enables AI agents to autonomously trade on Paloma DEX across 7 EVM chains.

## Overview

This MCP server provides AI agents with tools to perform decentralized trading operations on Paloma DEX, supporting cross-chain functionality across Ethereum, Arbitrum, Optimism, Base, BSC, Polygon, and Gnosis chains. The server prioritizes automation over security by enabling autonomous transaction execution through environment-based private key management.

## Features

### Core Trading Tools

- **`buy_token`**: Purchase ETF tokens or PUSD using any input token
- **`sell_token`**: Sell ETF tokens or PUSD back to other tokens  
- **`get_balance`**: Check token balances across all 7 supported chains
- **`get_price`**: Get current token prices

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

- **Autonomous Trading**: AI agents can execute transactions independently
- **Cross-Chain Support**: Works across all Paloma DEX supported chains
- **Gas Management**: Handles gas estimation and protocol fees automatically
- **Token Approvals**: Automatic approval handling for ERC20 tokens
- **Error Handling**: Comprehensive transaction error management
- **Contract Integration**: Ready integration with PUSD and ETF connector contracts

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
uv run python main.py
```

The server will start and listen for MCP protocol messages via stdin/stdout.

### Tool Examples

#### Buy Tokens
```json
{
  "tool": "buy_token",
  "arguments": {
    "chain_id": "1",
    "input_token_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "output_token_address": "0x...",
    "input_amount": "100.0",
    "slippage": 2.0
  }
}
```

#### Sell Tokens
```json
{
  "tool": "sell_token",
  "arguments": {
    "chain_id": "1", 
    "token_address": "0x...",
    "amount": "50.0"
  }
}
```

#### Check Balances
```json
{
  "tool": "get_balance",
  "arguments": {
    "chain_id": "1"
  }
}
```

#### Get Prices
```json
{
  "tool": "get_price",
  "arguments": {
    "chain_id": "1",
    "token_address": "0x..."
  }
}
```

## Architecture

### Core Components

- **`padex.py`**: Main MCP server implementation with all trading tools
- **`main.py`**: Entry point that launches the MCP server
- **Contract ABIs**: Simplified ABIs for PUSD and ETF connector interactions
- **Chain Configuration**: Complete configuration for all 7 supported chains

### Security Considerations

⚠️ **Important Security Notes**:
- This implementation prioritizes automation over security
- Private keys are stored in environment variables for autonomous operation
- Ensure your `.env` file is never committed to version control
- Consider using more secure key management for production use
- The `.gitignore` file excludes `.env` by default

### Dependencies

- **web3**: Ethereum blockchain interaction
- **eth-account**: Private key and transaction signing
- **eth-abi**: ABI encoding for contract calls
- **httpx**: HTTP client for API interactions
- **mcp**: Model Context Protocol implementation
- **python-dotenv**: Environment variable management

## API Integrations

The server integrates with:
- **Paloma DEX API**: For ETF data and custom pricing
- **Moralis API**: For balance and price data (optional)
- **Uniswap Protocol**: For swap path generation and routing

## Development

### Project Structure
```
mcpPADEX/
├── padex.py              # Main MCP server implementation
├── main.py               # Entry point
├── pyproject.toml        # Project dependencies
├── .env.example          # Environment variable template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

### Adding New Features

The server is designed to be extensible. To add new tools:

1. Define the tool in the `handle_list_tools()` method
2. Implement the tool handler in `handle_call_tool()`
3. Add the corresponding async method to the `PalomaDEXServer` class

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source. Please check the license file for details.

## Disclaimer

This software is provided "as is" without warranty. Trading cryptocurrencies involves risk of loss. Use at your own risk and ensure you understand the implications of automated trading before deployment.

## Support

For questions about Paloma DEX integration, consult the [Paloma DEX documentation](https://docs.palomachain.com/) or reach out to the Paloma team.

For MCP-related questions, see the [Model Context Protocol documentation](https://modelcontextprotocol.io/).
