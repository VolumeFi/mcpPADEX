#!/usr/bin/env python3
"""
Paloma DEX MCP Server (FastMCP Implementation)
Provides AI agents with tools to trade on Paloma DEX across 7 EVM chains.
"""

import asyncio
import json
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import httpx
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_abi import encode
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chain configurations
class ChainID(str, Enum):
    ETHEREUM_MAIN = "1"
    OPTIMISM_MAIN = "10"
    BSC_MAIN = "56"
    POLYGON_MAIN = "137"
    BASE_MAIN = "8453"
    ARBITRUM_MAIN = "42161"
    GNOSIS_MAIN = "100"

@dataclass
class ChainConfig:
    """Configuration for a blockchain network"""
    chain_id: int
    name: str
    rpc_url: str
    pusd_token: str
    pusd_connector: str
    etf_connector: str
    explorer_url: str
    gas_price_gwei: int = 20

# Chain configurations mapping
CHAIN_CONFIGS = {
    ChainID.ETHEREUM_MAIN: ChainConfig(
        chain_id=1,
        name="Ethereum",
        rpc_url="https://eth.llamarpc.com",
        pusd_token=os.getenv("PUSD_TOKEN_ETH", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_ETH", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_ETH", ""),
        explorer_url="https://etherscan.io",
        gas_price_gwei=30
    ),
    ChainID.ARBITRUM_MAIN: ChainConfig(
        chain_id=42161,
        name="Arbitrum One",
        rpc_url="https://arb1.arbitrum.io/rpc",
        pusd_token=os.getenv("PUSD_TOKEN_ARB", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_ARB", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_ARB", ""),
        explorer_url="https://arbiscan.io",
        gas_price_gwei=1
    ),
    ChainID.OPTIMISM_MAIN: ChainConfig(
        chain_id=10,
        name="Optimism",
        rpc_url="https://mainnet.optimism.io",
        pusd_token=os.getenv("PUSD_TOKEN_OP", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_OP", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_OP", ""),
        explorer_url="https://optimistic.etherscan.io",
        gas_price_gwei=1
    ),
    ChainID.BASE_MAIN: ChainConfig(
        chain_id=8453,
        name="Base",
        rpc_url="https://mainnet.base.org",
        pusd_token=os.getenv("PUSD_TOKEN_BASE", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_BASE", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_BASE", ""),
        explorer_url="https://basescan.org",
        gas_price_gwei=1
    ),
    ChainID.BSC_MAIN: ChainConfig(
        chain_id=56,
        name="BNB Smart Chain",
        rpc_url="https://bsc-dataseed1.binance.org",
        pusd_token=os.getenv("PUSD_TOKEN_BSC", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_BSC", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_BSC", ""),
        explorer_url="https://bscscan.com",
        gas_price_gwei=5
    ),
    ChainID.POLYGON_MAIN: ChainConfig(
        chain_id=137,
        name="Polygon",
        rpc_url="https://polygon-rpc.com",
        pusd_token=os.getenv("PUSD_TOKEN_MATIC", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_MATIC", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_MATIC", ""),
        explorer_url="https://polygonscan.com",
        gas_price_gwei=30
    ),
    ChainID.GNOSIS_MAIN: ChainConfig(
        chain_id=100,
        name="Gnosis Chain",
        rpc_url="https://rpc.gnosischain.com",
        pusd_token=os.getenv("PUSD_TOKEN_GNOSIS", ""),
        pusd_connector=os.getenv("PUSD_CONNECTOR_GNOSIS", ""),
        etf_connector=os.getenv("ETF_CONNECTOR_GNOSIS", ""),
        explorer_url="https://gnosisscan.io",
        gas_price_gwei=2
    )
}

@dataclass
class PalomaDEXContext:
    """Context for the Paloma DEX MCP server."""
    account: Account
    address: str
    private_key: str
    http_client: httpx.AsyncClient
    web3_clients: Dict[str, Web3]

@asynccontextmanager
async def paloma_dex_lifespan(server: FastMCP) -> AsyncIterator[PalomaDEXContext]:
    """Manages the Paloma DEX client lifecycle."""
    
    # Validate required environment variables
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY environment variable is required")
    
    # Initialize account
    account = Account.from_key(private_key)
    address = account.address
    
    logger.info(f"Initialized Paloma DEX server for address: {address}")
    
    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    # Initialize Web3 clients for each chain
    web3_clients = {}
    for chain_id, config in CHAIN_CONFIGS.items():
        try:
            web3_clients[chain_id] = Web3(Web3.HTTPProvider(config.rpc_url))
            logger.info(f"Connected to {config.name} ({chain_id})")
        except Exception as e:
            logger.warning(f"Failed to connect to {config.name}: {e}")
    
    try:
        yield PalomaDEXContext(
            account=account,
            address=address,
            private_key=private_key,
            http_client=http_client,
            web3_clients=web3_clients
        )
    finally:
        await http_client.aclose()
        logger.info("Paloma DEX server shutdown complete")

# Initialize FastMCP server
mcp = FastMCP(
    "paloma-dex",
    description="MCP server for Paloma DEX trading across 7 EVM chains",
    lifespan=paloma_dex_lifespan
)

# ERC-20 ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

# ETF Connector ABI (key functions)
ETF_CONNECTOR_ABI = [
    {
        "name": "buy",
        "type": "function",
        "inputs": [
            {"name": "etf_token", "type": "address"},
            {"name": "etf_amount", "type": "uint256"},
            {"name": "usd_amount", "type": "uint256"},
            {"name": "recipient", "type": "address"},
            {"name": "path", "type": "bytes"},
            {"name": "deadline", "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    },
    {
        "name": "sell",
        "type": "function",
        "inputs": [
            {"name": "etf_token", "type": "address"},
            {"name": "etf_amount", "type": "uint256"},
            {"name": "deadline", "type": "uint256"},
            {"name": "recipient", "type": "address"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    }
]

@mcp.tool()
async def get_account_info(ctx: Context) -> str:
    """Get account information including address and balances across all chains.
    
    Returns:
        JSON string with account address and native token balances on all supported chains.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        account_info = {
            "address": paloma_ctx.address,
            "balances": {}
        }
        
        for chain_id, config in CHAIN_CONFIGS.items():
            if chain_id in paloma_ctx.web3_clients:
                try:
                    web3 = paloma_ctx.web3_clients[chain_id]
                    balance_wei = web3.eth.get_balance(paloma_ctx.address)
                    balance_eth = web3.from_wei(balance_wei, 'ether')
                    
                    account_info["balances"][config.name] = {
                        "native_balance": str(balance_eth),
                        "chain_id": config.chain_id,
                        "symbol": "ETH" if chain_id == ChainID.ETHEREUM_MAIN else config.name.split()[0]
                    }
                except Exception as e:
                    account_info["balances"][config.name] = {"error": str(e)}
        
        return json.dumps(account_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return f"Error getting account info: {str(e)}"

@mcp.tool()
async def get_pusd_balance(ctx: Context, chain_id: str) -> str:
    """Get PUSD token balance on specified chain.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
    
    Returns:
        JSON string with PUSD balance information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        if not config.pusd_token:
            return f"Error: PUSD token address not configured for {config.name}"
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        pusd_contract = web3.eth.contract(
            address=config.pusd_token,
            abi=ERC20_ABI
        )
        
        balance_wei = pusd_contract.functions.balanceOf(paloma_ctx.address).call()
        decimals = pusd_contract.functions.decimals().call()
        balance = balance_wei / (10 ** decimals)
        
        balance_info = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "token_address": config.pusd_token,
            "balance": str(balance),
            "symbol": "PUSD",
            "decimals": decimals
        }
        
        return json.dumps(balance_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting PUSD balance: {e}")
        return f"Error getting PUSD balance: {str(e)}"

@mcp.tool()
async def get_chain_info(ctx: Context, chain_id: str) -> str:
    """Get detailed information about a specific chain.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
    
    Returns:
        JSON string with chain configuration and status.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            available_chains = [str(k) for k in CHAIN_CONFIGS.keys()]
            return f"Error: Unsupported chain ID '{chain_id}'. Available: {available_chains}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        chain_info = {
            "chain_id": config.chain_id,
            "name": config.name,
            "rpc_url": config.rpc_url,
            "explorer_url": config.explorer_url,
            "gas_price_gwei": config.gas_price_gwei,
            "contracts": {
                "pusd_token": config.pusd_token or "Not configured",
                "pusd_connector": config.pusd_connector or "Not configured",
                "etf_connector": config.etf_connector or "Not configured"
            }
        }
        
        # Add connection status
        if chain_id in paloma_ctx.web3_clients:
            try:
                web3 = paloma_ctx.web3_clients[chain_id]
                latest_block = web3.eth.get_block('latest')
                chain_info["status"] = "connected"
                chain_info["latest_block"] = latest_block.number
            except Exception as e:
                chain_info["status"] = f"connection_error: {str(e)}"
        else:
            chain_info["status"] = "not_connected"
        
        return json.dumps(chain_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting chain info: {e}")
        return f"Error getting chain info: {str(e)}"

@mcp.tool()
async def list_supported_chains(ctx: Context) -> str:
    """List all supported chains with their configurations.
    
    Returns:
        JSON string with all supported chain information.
    """
    try:
        chains_info = {}
        
        for chain_id, config in CHAIN_CONFIGS.items():
            chains_info[chain_id] = {
                "chain_id": config.chain_id,
                "name": config.name,
                "rpc_url": config.rpc_url,
                "explorer_url": config.explorer_url,
                "has_pusd_token": bool(config.pusd_token),
                "has_pusd_connector": bool(config.pusd_connector),
                "has_etf_connector": bool(config.etf_connector)
            }
        
        return json.dumps(chains_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing chains: {e}")
        return f"Error listing chains: {str(e)}"

@mcp.tool()
async def get_address_balances(ctx: Context, address: str) -> str:
    """Get balances for a specific address across all chains.
    
    Args:
        address: Ethereum address to check balances for
    
    Returns:
        JSON string with balance information across all chains.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        # Validate address
        if not Web3.is_address(address):
            return f"Error: Invalid address format: {address}"
        
        address = Web3.to_checksum_address(address)
        balances = {}
        
        for chain_id, config in CHAIN_CONFIGS.items():
            if chain_id in paloma_ctx.web3_clients:
                try:
                    web3 = paloma_ctx.web3_clients[chain_id]
                    
                    # Get native balance
                    native_balance_wei = web3.eth.get_balance(address)
                    native_balance = web3.from_wei(native_balance_wei, 'ether')
                    
                    chain_balances = {
                        "native_balance": str(native_balance),
                        "native_symbol": "ETH" if chain_id == ChainID.ETHEREUM_MAIN else config.name.split()[0]
                    }
                    
                    # Get PUSD balance if configured
                    if config.pusd_token:
                        try:
                            pusd_contract = web3.eth.contract(
                                address=config.pusd_token,
                                abi=ERC20_ABI
                            )
                            pusd_balance_wei = pusd_contract.functions.balanceOf(address).call()
                            pusd_decimals = pusd_contract.functions.decimals().call()
                            pusd_balance = pusd_balance_wei / (10 ** pusd_decimals)
                            chain_balances["pusd_balance"] = str(pusd_balance)
                        except Exception as e:
                            chain_balances["pusd_balance"] = f"Error: {str(e)}"
                    
                    balances[config.name] = chain_balances
                    
                except Exception as e:
                    balances[config.name] = {"error": str(e)}
        
        result = {
            "address": address,
            "balances": balances,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting address balances: {e}")
        return f"Error getting address balances: {str(e)}"

# Helper function for chain name mapping
def get_chain_name_for_api(chain_id: str) -> Optional[str]:
    """Map chain ID to chain name for Paloma DEX API calls."""
    chain_name_mapping = {
        "1": "ethereum",
        "10": "optimism", 
        "56": "bsc",
        "100": "gnosis",
        "137": "polygon",
        "8453": "base",
        "42161": "arbitrum"
    }
    return chain_name_mapping.get(chain_id)

@mcp.tool()
async def get_etf_tokens(ctx: Context, chain_id: str) -> str:
    """Get available ETF tokens on a specific chain.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
    
    Returns:
        JSON string with available ETF tokens and their information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        chain_name = get_chain_name_for_api(chain_id)
        if not chain_name:
            return f"Error: Chain name mapping not found for chain ID {chain_id}"
        
        # Call Paloma DEX API to get ETF tokens
        api_url = f"https://api.palomadex.com/etfapi/v1/etf?chain_id={chain_name}"
        
        response = await paloma_ctx.http_client.get(api_url)
        if response.status_code == 200:
            etf_data = response.json()
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "etf_connector": config.etf_connector or "Not configured",
                "etf_tokens": etf_data
            }
            
            return json.dumps(result, indent=2)
        else:
            return f"Error: Failed to fetch ETF tokens. Status: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error getting ETF tokens: {e}")
        return f"Error getting ETF tokens: {str(e)}"

@mcp.tool()
async def get_etf_price(ctx: Context, chain_id: str, etf_token_address: str) -> str:
    """Get buy and sell prices for an ETF token.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        etf_token_address: Address of the ETF token
    
    Returns:
        JSON string with buy and sell prices for the ETF token.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        # Validate ETF token address
        if not Web3.is_address(etf_token_address):
            return f"Error: Invalid ETF token address format: {etf_token_address}"
        
        chain_name = get_chain_name_for_api(chain_id)
        if not chain_name:
            return f"Error: Chain name mapping not found for chain ID {chain_id}"
        
        # Call Paloma DEX API to get custom pricing
        api_url = f"https://api.palomadx.com/etfapi/v1/customindexprice?chain_id={chain_name}&token_evm_address={etf_token_address}"
        
        response = await paloma_ctx.http_client.get(api_url)
        if response.status_code == 200:
            price_data = response.json()
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "etf_token_address": etf_token_address,
                "pricing": price_data,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return json.dumps(result, indent=2)
        else:
            return f"Error: Failed to fetch ETF price. Status: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error getting ETF price: {e}")
        return f"Error getting ETF price: {str(e)}"

@mcp.tool()
async def get_etf_balance(ctx: Context, chain_id: str, etf_token_address: str, wallet_address: Optional[str] = None) -> str:
    """Get ETF token balance for a wallet address.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        etf_token_address: Address of the ETF token
        wallet_address: Wallet address to check (defaults to server wallet)
    
    Returns:
        JSON string with ETF token balance information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        # Use server wallet if no address provided
        if wallet_address is None:
            wallet_address = paloma_ctx.address
        
        # Validate addresses
        if not Web3.is_address(etf_token_address):
            return f"Error: Invalid ETF token address format: {etf_token_address}"
        
        if not Web3.is_address(wallet_address):
            return f"Error: Invalid wallet address format: {wallet_address}"
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        etf_contract = web3.eth.contract(
            address=etf_token_address,
            abi=ERC20_ABI
        )
        
        # Get token info
        try:
            balance_wei = etf_contract.functions.balanceOf(wallet_address).call()
            decimals = etf_contract.functions.decimals().call()
            symbol = etf_contract.functions.symbol().call()
            balance = balance_wei / (10 ** decimals)
        except Exception as e:
            return f"Error: Failed to read ETF token contract: {str(e)}"
        
        balance_info = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "wallet_address": wallet_address,
            "etf_token_address": etf_token_address,
            "symbol": symbol,
            "balance": str(balance),
            "balance_wei": str(balance_wei),
            "decimals": decimals
        }
        
        return json.dumps(balance_info, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting ETF balance: {e}")
        return f"Error getting ETF balance: {str(e)}"

@mcp.tool()
async def buy_etf_token(ctx: Context, chain_id: str, etf_token_address: str, input_token_address: str, input_amount: str, slippage: float = 2.0) -> str:
    """Buy ETF tokens using input tokens (simulation only - no actual transaction).
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        etf_token_address: Address of the ETF token to buy
        input_token_address: Address of token to spend (use 'native' for ETH/BNB/MATIC/xDAI)
        input_amount: Amount of input token to spend (in token units, e.g. '1.5')
        slippage: Slippage tolerance as percentage (default: 2.0)
    
    Returns:
        JSON string with transaction simulation details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if not config.etf_connector:
            return f"Error: ETF connector not configured for {config.name}"
        
        # Validate addresses
        if not Web3.is_address(etf_token_address):
            return f"Error: Invalid ETF token address format: {etf_token_address}"
        
        if input_token_address != 'native' and not Web3.is_address(input_token_address):
            return f"Error: Invalid input token address format: {input_token_address}"
        
        try:
            input_amount_float = float(input_amount)
            if input_amount_float <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid input amount: {input_amount}"
        
        # Get ETF token information
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        
        try:
            etf_contract = web3.eth.contract(address=etf_token_address, abi=ERC20_ABI)
            etf_symbol = etf_contract.functions.symbol().call()
            etf_decimals = etf_contract.functions.decimals().call()
        except Exception as e:
            return f"Error: Failed to read ETF token contract: {str(e)}"
        
        # Get input token information
        if input_token_address == 'native':
            input_symbol = "ETH" if chain_id == ChainID.ETHEREUM_MAIN else config.name.split()[0]
            input_decimals = 18
        else:
            try:
                input_contract = web3.eth.contract(address=input_token_address, abi=ERC20_ABI)
                input_symbol = input_contract.functions.symbol().call()
                input_decimals = input_contract.functions.decimals().call()
            except Exception as e:
                return f"Error: Failed to read input token contract: {str(e)}"
        
        # Simulate transaction details (no actual execution)
        simulation_result = {
            "operation": "buy_etf_token",
            "chain": config.name,
            "chain_id": config.chain_id,
            "etf_connector": config.etf_connector,
            "input_token": {
                "address": input_token_address,
                "symbol": input_symbol,
                "amount": input_amount,
                "decimals": input_decimals
            },
            "output_token": {
                "address": etf_token_address,
                "symbol": etf_symbol,
                "decimals": etf_decimals
            },
            "slippage": slippage,
            "status": "simulation",
            "note": "This is a simulation. Actual trading requires additional path generation and approval steps.",
            "next_steps": [
                "1. Get swap path via Uniswap for price calculation",
                "2. Approve input token spending to ETF connector",
                "3. Call ETF connector buy() function with proper parameters",
                "4. Handle gas fees and transaction confirmation"
            ]
        }
        
        return json.dumps(simulation_result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in buy ETF token simulation: {e}")
        return f"Error in buy ETF token simulation: {str(e)}"

@mcp.tool()
async def sell_etf_token(ctx: Context, chain_id: str, etf_token_address: str, etf_amount: str) -> str:
    """Sell ETF tokens back to base currency (simulation only - no actual transaction).
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        etf_token_address: Address of the ETF token to sell
        etf_amount: Amount of ETF tokens to sell (in token units, e.g. '10.5')
    
    Returns:
        JSON string with transaction simulation details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if not config.etf_connector:
            return f"Error: ETF connector not configured for {config.name}"
        
        # Validate addresses
        if not Web3.is_address(etf_token_address):
            return f"Error: Invalid ETF token address format: {etf_token_address}"
        
        try:
            etf_amount_float = float(etf_amount)
            if etf_amount_float <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid ETF amount: {etf_amount}"
        
        # Get ETF token information
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        
        try:
            etf_contract = web3.eth.contract(address=etf_token_address, abi=ERC20_ABI)
            etf_symbol = etf_contract.functions.symbol().call()
            etf_decimals = etf_contract.functions.decimals().call()
            
            # Check current balance
            balance_wei = etf_contract.functions.balanceOf(paloma_ctx.address).call()
            balance = balance_wei / (10 ** etf_decimals)
            
        except Exception as e:
            return f"Error: Failed to read ETF token contract: {str(e)}"
        
        # Check if user has sufficient balance
        if etf_amount_float > balance:
            return f"Error: Insufficient balance. You have {balance} {etf_symbol}, trying to sell {etf_amount}"
        
        # Simulate transaction details (no actual execution)
        simulation_result = {
            "operation": "sell_etf_token",
            "chain": config.name,
            "chain_id": config.chain_id,
            "etf_connector": config.etf_connector,
            "etf_token": {
                "address": etf_token_address,
                "symbol": etf_symbol,
                "amount_to_sell": etf_amount,
                "current_balance": str(balance),
                "decimals": etf_decimals
            },
            "recipient": paloma_ctx.address,
            "status": "simulation",
            "note": "This is a simulation. Actual trading requires approval and proper transaction execution.",
            "next_steps": [
                "1. Approve ETF token spending to ETF connector",
                "2. Call ETF connector sell() function with deadline parameter",
                "3. Handle gas fees and transaction confirmation",
                "4. Receive proceeds in base currency"
            ]
        }
        
        return json.dumps(simulation_result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in sell ETF token simulation: {e}")
        return f"Error in sell ETF token simulation: {str(e)}"

async def main():
    """Main function to run the MCP server."""
    transport = os.getenv("TRANSPORT", "stdio")
    
    if transport == "stdio":
        await mcp.run_stdio_async()
    elif transport == "sse":
        await mcp.run_sse_async()
    else:
        logger.error(f"Unsupported transport: {transport}")
        return

if __name__ == "__main__":
    asyncio.run(main())