# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is mcpPADEX, a Paloma DEX MCP Server implementation using the FastMCP framework. The project provides AI agents with tools to interact with Paloma DEX across 7 EVM chains.

## Development Commands

The project uses uv for package management:

- Install dependencies: `uv sync`
- Run the MCP server: `uv run padex.py`
- Run the basic entry point: `uv run python main.py`
- Test specific tools: `uv run python <script_name>.py`

## Architecture

- `padex.py`: Main FastMCP server implementation with blockchain tools
- `padex_old.py`: Previous low-level MCP implementation (backup)
- `main.py`: Simple entry point with "Hello World" functionality
- `pyproject.toml`: Project configuration with Web3 and MCP dependencies
- `.env`: Environment variables including private key and contract addresses

## Key Components

### MCP Tools Available
- `get_account_info`: Account address and native balances across all chains
- `get_pusd_balance`: PUSD token balance on specific chain
- `get_chain_info`: Detailed chain information and status
- `list_supported_chains`: All supported chain configurations
- `get_address_balances`: Balances for any Ethereum address

### Supported Chains
- Ethereum (1), Arbitrum (42161), Optimism (10), Base (8453)
- BSC (56), Polygon (137), Gnosis (100)

### Dependencies

- **mcp[cli]**: FastMCP framework for MCP server implementation
- **web3**: Ethereum blockchain interaction
- **eth-account**: Private key and transaction signing
- **eth-abi**: ABI encoding for contract calls
- **httpx**: HTTP client for API interactions
- **python-dotenv**: Environment variable management

## Environment Setup

Required environment variables in `.env`:
- `PRIVATE_KEY`: Ethereum private key for wallet operations
- `PUSD_TOKEN_*`: PUSD token addresses for each chain
- `PUSD_CONNECTOR_*`: PUSD connector contract addresses
- `ETF_CONNECTOR_*`: ETF connector contract addresses
- `MORALIS_SERVICE_API_KEY`: Optional Moralis API key

The project requires Python 3.12 or higher.