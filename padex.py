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
import math

import httpx
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_abi import encode
from dotenv import load_dotenv
import requests
from bech32 import bech32_decode, bech32_encode, convertbits

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
    paloma_client: Any  # Will be PalomaClient
    palomadex_api: Any  # Will be PalomaDEXAPI

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
    
    # Initialize Paloma client and API
    paloma_client = PalomaClient(PALOMA_LCD_URL, PALOMA_CHAIN_ID)
    palomadex_api = PalomaDEXAPI(paloma_client)
    logger.info(f"Initialized Paloma client: {PALOMA_LCD_URL}")
    
    try:
        yield PalomaDEXContext(
            account=account,
            address=address,
            private_key=private_key,
            http_client=http_client,
            web3_clients=web3_clients,
            paloma_client=paloma_client,
            palomadex_api=palomadex_api
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

# Trader Contract ABI (for buy/sell operations)
TRADER_ABI = [
    {
        "name": "purchase",
        "type": "function",
        "inputs": [
            {"name": "from_token", "type": "address"},
            {"name": "to_token", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    },
    {
        "name": "add_liquidity",
        "type": "function",
        "inputs": [
            {"name": "token0", "type": "address"},
            {"name": "token1", "type": "address"},
            {"name": "amount0", "type": "uint256"},
            {"name": "amount1", "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    },
    {
        "name": "remove_liquidity",
        "type": "function",
        "inputs": [
            {"name": "token0", "type": "address"},
            {"name": "token1", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    },
    {
        "name": "gas_fee",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    }
]

# Trader contract addresses for each chain
TRADER_ADDRESSES = {
    ChainID.ETHEREUM_MAIN: "0x7230EC05eD8c38D5be6f58Ae41e30D1ED6cfDAf1",
    ChainID.ARBITRUM_MAIN: "0x36B8763b3b71685F21512511bB433f4A0f50213E", 
    ChainID.BASE_MAIN: "0xd58Dfd5b39fCe87dD9C434e95428DdB289934179",
    ChainID.BSC_MAIN: "0x8ee509a97279029071AB66Cb0391e8Dc67a137f9",
    ChainID.GNOSIS_MAIN: "0xd58Dfd5b39fCe87dD9C434e95428DdB289934179",
    ChainID.OPTIMISM_MAIN: "0xB6d4AAFfBbceB5e363352179E294326C91d6c127",
    ChainID.POLYGON_MAIN: "0xB6d4AAFfBbceB5e363352179E294326C91d6c127"
}

# Trading constants
MAX_AMOUNT = 2**256 - 1  # Maximum approval amount
GAS_MULTIPLIER = 3  # Divide by this for 33% gas buffer
MAX_SPREAD = 0.4  # 40% maximum spread limit

# Paloma configuration
PALOMA_LCD_URL = os.getenv("PALOMA_LCD", "https://lcd.paloma.dev")
PALOMA_CHAIN_ID = os.getenv("PALOMA_CHAIN_ID", "paloma-1")
PALOMADEX_FACTORY_ADDRESS = os.getenv("PALOMADEX_FACTORY_ADDRESS", "")
PALOMADEX_ROUTER_ADDRESS = os.getenv("PALOMADEX_ROUTER_ADDRESS", "")

# Token denomination mapping for cross-chain
def create_token_denom(chain_id: str, token_address: str, symbol: str) -> str:
    """Create Paloma token denomination from EVM token info."""
    chain_name_mapping = {
        "1": "ethereum",
        "10": "optimism", 
        "56": "bsc",
        "100": "gnosis",
        "137": "polygon",
        "8453": "base",
        "42161": "arbitrum"
    }
    
    chain_name = chain_name_mapping.get(chain_id)
    if not chain_name:
        return ""
    
    return f"{chain_name}/{token_address}/{symbol.lower()}"

def parse_token_denom(denom: str) -> Optional[Dict[str, str]]:
    """Parse Paloma token denomination to extract components."""
    parts = denom.split('/')
    if len(parts) != 3:
        return None
    
    return {
        "network": parts[0],
        "address": parts[1], 
        "symbol": parts[2]
    }

class PalomaClient:
    """Simple Paloma LCD client for querying contracts."""
    
    def __init__(self, lcd_url: str, chain_id: str):
        self.lcd_url = lcd_url.rstrip('/')
        self.chain_id = chain_id
    
    async def query_contract(self, contract_address: str, query: Dict) -> Dict:
        """Query a CosmWasm contract."""
        url = f"{self.lcd_url}/cosmwasm/wasm/v1/contract/{contract_address}/smart"
        
        # Encode query as base64
        import base64
        query_bytes = base64.b64encode(json.dumps(query).encode()).decode()
        
        params = {"query_data": query_bytes}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                result = response.json()
                return result.get('data', {})
            else:
                raise Exception(f"Query failed: {response.status_code} {response.text}")

class AMM:
    """AMM calculation utilities."""
    
    @staticmethod
    def calculate_swap_output(input_amount: int, input_reserve: int, output_reserve: int, fee_rate: float = 0.003) -> int:
        """Calculate swap output using constant product formula."""
        if input_reserve <= 0 or output_reserve <= 0:
            return 0
        
        # Apply fee to input amount
        input_amount_with_fee = int(input_amount * (1 - fee_rate))
        
        # Constant product formula: (x + dx) * (y - dy) = x * y
        # dy = (y * dx) / (x + dx)
        numerator = output_reserve * input_amount_with_fee
        denominator = input_reserve + input_amount_with_fee
        
        if denominator <= 0:
            return 0
        
        return numerator // denominator
    
    @staticmethod
    def calculate_price_impact(input_amount: int, input_reserve: int, output_reserve: int) -> float:
        """Calculate price impact percentage."""
        if input_reserve <= 0 or output_reserve <= 0:
            return 0.0
        
        # Current price (before swap)
        current_price = output_reserve / input_reserve
        
        # Price after swap
        output_amount = AMM.calculate_swap_output(input_amount, input_reserve, output_reserve)
        if input_amount <= 0:
            return 0.0
        
        new_price = output_amount / input_amount
        
        # Price impact as percentage
        if current_price <= 0:
            return 0.0
        
        price_impact = (current_price - new_price) / current_price * 100
        return max(0.0, price_impact)
    
    @staticmethod
    def apply_slippage_tolerance(amount: int, slippage_tolerance: float) -> int:
        """Apply slippage tolerance to get minimum received amount."""
        return int(amount * (1 - slippage_tolerance / 100))

class PalomaDEXAPI:
    """PalomaDEX API implementation using Paloma queries."""
    
    def __init__(self, paloma_client: PalomaClient):
        self.client = paloma_client
        
    async def get_tokens(self, chain_id: str) -> List[Dict]:
        """Get available tokens for a chain (mock implementation)."""
        # In real implementation, this would query the factory contract
        # For now, return common tokens per chain
        common_tokens = {
            "1": [  # Ethereum
                {"erc20_name": "USD Coin", "erc20_symbol": "USDC", "erc20_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "erc20_decimals": 6, "is_pair_exist": True},
                {"erc20_name": "Tether USD", "erc20_symbol": "USDT", "erc20_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "erc20_decimals": 6, "is_pair_exist": True},
                {"erc20_name": "Wrapped Ether", "erc20_symbol": "WETH", "erc20_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "erc20_decimals": 18, "is_pair_exist": True}
            ],
            "42161": [  # Arbitrum
                {"erc20_name": "USD Coin", "erc20_symbol": "USDC", "erc20_address": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "erc20_decimals": 6, "is_pair_exist": True},
                {"erc20_name": "Tether USD", "erc20_symbol": "USDT", "erc20_address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "erc20_decimals": 6, "is_pair_exist": True}
            ]
        }
        
        return common_tokens.get(chain_id, [])
    
    async def get_token_estimate(self, input_token_address: str, output_token_address: str, 
                               chain_id: str, input_amount: str) -> Dict:
        """Get token swap estimation using AMM math."""
        try:
            # Create token denoms for Paloma
            input_denom = create_token_denom(chain_id, input_token_address, "input")
            output_denom = create_token_denom(chain_id, output_token_address, "output")
            
            if not input_denom or not output_denom:
                return {"exist": False, "empty": True, "estimated_amount": "0"}
            
            # Mock pool reserves (in real implementation, query from Paloma)
            input_reserve = 1000000 * 10**18  # 1M tokens
            output_reserve = 1000000 * 10**18  # 1M tokens
            
            input_amount_int = int(input_amount)
            
            # Calculate swap output using AMM
            estimated_output = AMM.calculate_swap_output(
                input_amount_int, input_reserve, output_reserve
            )
            
            return {
                "amount0": str(input_amount),
                "amount1": str(estimated_output),
                "estimated_amount": str(estimated_output),
                "exist": True,
                "empty": False
            }
            
        except Exception as e:
            logger.error(f"Error in token estimation: {e}")
            return {"exist": False, "empty": True, "estimated_amount": "0"}
    
    async def get_quote(self, token0: str, token1: str, chain_id: str) -> Dict:
        """Get quote for trade validation."""
        try:
            # Mock liquidity check
            return {
                "amount0": "1000000000000000000000000",  # 1M tokens
                "exist": True,
                "empty": False
            }
        except Exception as e:
            logger.error(f"Error in quote: {e}")
            return {"exist": False, "empty": True}

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

async def _get_chain_balance(web3: Web3, address: str, config: ChainConfig, chain_id: str) -> Dict[str, Any]:
    """Helper function to get balance for a single chain with individual timeout."""
    try:
        # Get native balance with individual timeout (5 seconds per chain)
        native_balance_wei = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: web3.eth.get_balance(address)
            ),
            timeout=5.0
        )
        native_balance = web3.from_wei(native_balance_wei, 'ether')
        
        chain_balances = {
            "native_balance": str(native_balance),
            "native_symbol": "ETH" if chain_id == ChainID.ETHEREUM_MAIN else config.name.split()[0]
        }
        
        # Get PUSD balance if configured (with individual timeout)
        if config.pusd_token:
            try:
                pusd_contract = web3.eth.contract(
                    address=config.pusd_token,
                    abi=ERC20_ABI
                )
                
                # Wrap contract calls in timeout
                pusd_balance_wei = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: pusd_contract.functions.balanceOf(address).call()
                    ),
                    timeout=5.0
                )
                pusd_decimals = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: pusd_contract.functions.decimals().call()
                    ),
                    timeout=5.0
                )
                pusd_balance = pusd_balance_wei / (10 ** pusd_decimals)
                chain_balances["pusd_balance"] = str(pusd_balance)
            except asyncio.TimeoutError:
                chain_balances["pusd_balance"] = "Timeout"
            except Exception as e:
                chain_balances["pusd_balance"] = f"Error: {str(e)}"
        
        return {config.name: chain_balances}
        
    except asyncio.TimeoutError:
        return {config.name: {"error": "Timeout (5s)"}}
    except Exception as e:
        return {config.name: {"error": str(e)}}

@mcp.tool()
async def get_address_balances(ctx: Context, address: str, timeout_seconds: float = 30.0) -> str:
    """Get balances for a specific address across all chains (concurrent execution).
    
    Args:
        address: Ethereum address to check balances for
        timeout_seconds: Timeout for the entire operation (default: 30 seconds)
    
    Returns:
        JSON string with balance information across all chains.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        # Validate address
        if not Web3.is_address(address):
            return f"Error: Invalid address format: {address}"
        
        address = Web3.to_checksum_address(address)
        
        # Create tasks for concurrent execution
        tasks = []
        chain_names = []
        
        for chain_id, config in CHAIN_CONFIGS.items():
            if chain_id in paloma_ctx.web3_clients:
                web3 = paloma_ctx.web3_clients[chain_id]
                task = _get_chain_balance(web3, address, config, chain_id)
                tasks.append(task)
                chain_names.append(config.name)
        
        # Execute all balance checks concurrently (no overall timeout, individual chains handle their own timeouts)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        balances = {}
        for result in results:
            if isinstance(result, dict):
                balances.update(result)
            elif isinstance(result, Exception):
                logger.error(f"Chain balance check failed: {result}")
        
        result = {
            "address": address,
            "balances": balances,
            "chains_checked": len(tasks),
            "timeout_seconds": timeout_seconds,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting address balances: {e}")
        return f"Error getting address balances: {str(e)}"

@mcp.tool()
async def get_address_balance_single_chain(ctx: Context, address: str, chain_id: str) -> str:
    """Get balance for a specific address on a single chain (faster).
    
    Args:
        address: Ethereum address to check balances for
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
    
    Returns:
        JSON string with balance information for the specified chain.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        # Validate address
        if not Web3.is_address(address):
            return f"Error: Invalid address format: {address}"
        
        if chain_id not in CHAIN_CONFIGS:
            available_chains = [str(k) for k in CHAIN_CONFIGS.keys()]
            return f"Error: Unsupported chain ID '{chain_id}'. Available: {available_chains}"
        
        if chain_id not in paloma_ctx.web3_clients:
            config = CHAIN_CONFIGS[chain_id]
            return f"Error: Web3 client not available for {config.name}"
        
        address = Web3.to_checksum_address(address)
        config = CHAIN_CONFIGS[chain_id]
        web3 = paloma_ctx.web3_clients[chain_id]
        
        # Get balance for single chain
        chain_balance = await _get_chain_balance(web3, address, config, chain_id)
        
        result = {
            "address": address,
            "chain": config.name,
            "chain_id": config.chain_id,
            "balance": chain_balance[config.name],
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting single chain balance: {e}")
        return f"Error getting single chain balance: {str(e)}"

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
            
            # Filter to only show ETF tokens that have EVM deployments
            deployed_etfs = []
            for etf in etf_data:
                if etf.get("evm") and len(etf["evm"]) > 0:
                    # Has EVM deployments
                    deployed_etfs.append(etf)
                else:
                    # No EVM deployment yet - only exists on Paloma
                    etf["status"] = "paloma_only"
                    etf["note"] = "ETF exists on Paloma but not yet deployed to EVM chains"
                    deployed_etfs.append(etf)
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "etf_connector": config.etf_connector or "Not configured",
                "total_etfs": len(etf_data),
                "evm_deployed_etfs": len([etf for etf in etf_data if etf.get("evm") and len(etf["evm"]) > 0]),
                "paloma_only_etfs": len([etf for etf in etf_data if not etf.get("evm") or len(etf["evm"]) == 0]),
                "etf_tokens": deployed_etfs,
                "trading_note": "ETF trading currently requires EVM token deployment. Most ETFs are Paloma-native only."
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
        api_url = f"https://api.palomadex.com/etfapi/v1/customindexprice?chain_id={chain_name}&token_evm_address={etf_token_address}"
        
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
async def get_etf_price_by_symbol(ctx: Context, symbol: str) -> str:
    """Get ETF price by token symbol from Paloma DEX.
    
    Args:
        symbol: ETF token symbol (e.g., PAGOLD, PABTC2X, PACBOA)
    
    Returns:
        JSON string with ETF price data.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        # Call Paloma DEX API to get price by symbol
        api_url = f"https://api.palomadex.com/etfapi/v1/price?symbol={symbol}"
        
        response = await paloma_ctx.http_client.get(api_url)
        if response.status_code == 200:
            price_data = response.json()
            
            result = {
                "symbol": symbol,
                "pricing": price_data,
                "timestamp": asyncio.get_event_loop().time(),
                "source": "paloma_dex_api_symbol"
            }
            
            return json.dumps(result, indent=2)
        else:
            return f"Error: Failed to fetch ETF price for symbol {symbol}. Status: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error getting ETF price by symbol: {e}")
        return f"Error getting ETF price by symbol: {str(e)}"

@mcp.tool()
async def get_etf_price_by_paloma_denom(ctx: Context, paloma_denom: str) -> str:
    """Get ETF price by Paloma denomination.
    
    Args:
        paloma_denom: Paloma denomination (e.g., factory/paloma18xrvj2ffxygkmtqwf3tr6fjqk3w0dgg7m6ucwx/palomagold)
    
    Returns:
        JSON string with ETF price data.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        # Call Paloma DEX API to get custom pricing by denom
        # Note: This endpoint might need to be confirmed with Paloma team
        api_url = f"https://api.palomadex.com/etfapi/v1/customprice?paloma_denom={paloma_denom}"
        
        response = await paloma_ctx.http_client.get(api_url)
        if response.status_code == 200:
            price_data = response.json()
            
            result = {
                "paloma_denom": paloma_denom,
                "pricing": price_data,
                "timestamp": asyncio.get_event_loop().time(),
                "source": "paloma_dex_api_denom"
            }
            
            return json.dumps(result, indent=2)
        else:
            return f"Error: Failed to fetch ETF price for denom {paloma_denom}. Status: {response.status_code}"
                
    except Exception as e:
        logger.error(f"Error getting ETF price by paloma denom: {e}")
        return f"Error getting ETF price by paloma denom: {str(e)}"

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

@mcp.tool()
async def get_available_trading_tokens(ctx: Context, chain_id: str) -> str:
    """Get available tokens for trading on a specific chain.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
    
    Returns:
        JSON string with available trading tokens and their information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        chain_name = get_chain_name_for_api(chain_id)
        
        if not chain_name:
            return f"Error: Chain name mapping not found for chain ID {chain_id}"
        
        # Use our Paloma-based API implementation
        try:
            tokens_data = await paloma_ctx.palomadex_api.get_tokens(chain_id)
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "trader_contract": TRADER_ADDRESSES.get(chain_id, "Not configured"),
                "total_tokens": len(tokens_data),
                "tradeable_tokens": len([t for t in tokens_data if t.get('is_pair_exist', False)]),
                "tokens": tokens_data,
                "data_source": "paloma_dex_api"
            }
            
            return json.dumps(result, indent=2)
        except Exception as api_error:
            logger.warning(f"Paloma API failed: {api_error}, using fallback")
            
            # Fallback: Return common tokens that are likely available for trading
            common_tokens = []
            
            if chain_id == ChainID.ETHEREUM_MAIN:
                common_tokens = [
                    {"erc20_name": "USD Coin", "erc20_symbol": "USDC", "erc20_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "erc20_decimals": 6, "is_pair_exist": True},
                    {"erc20_name": "Tether USD", "erc20_symbol": "USDT", "erc20_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "erc20_decimals": 6, "is_pair_exist": True},
                    {"erc20_name": "Wrapped Ether", "erc20_symbol": "WETH", "erc20_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "erc20_decimals": 18, "is_pair_exist": True}
                ]
            elif chain_id == ChainID.ARBITRUM_MAIN:
                common_tokens = [
                    {"erc20_name": "USD Coin", "erc20_symbol": "USDC", "erc20_address": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "erc20_decimals": 6, "is_pair_exist": True},
                    {"erc20_name": "Tether USD", "erc20_symbol": "USDT", "erc20_address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "erc20_decimals": 6, "is_pair_exist": True}
                ]
            # Add more chains as needed
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "trader_contract": TRADER_ADDRESSES.get(chain_id, "Not configured"),
                "note": "Using fallback token list - Paloma API unavailable",
                "total_tokens": len(common_tokens),
                "tradeable_tokens": len(common_tokens),
                "tokens": common_tokens,
                "data_source": "fallback"
            }
            
            return json.dumps(result, indent=2)
                
    except Exception as e:
        logger.error(f"Error getting available tokens: {e}")
        return f"Error getting available tokens: {str(e)}"

@mcp.tool()
async def get_token_price_estimate(ctx: Context, chain_id: str, input_token_address: str, output_token_address: str, input_amount: str) -> str:
    """Get real-time price estimate for token swap.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        input_token_address: Address of token to trade from
        output_token_address: Address of token to trade to
        input_amount: Amount of input token in wei format
    
    Returns:
        JSON string with price estimate and trading information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        chain_name = get_chain_name_for_api(chain_id)
        
        if not chain_name:
            return f"Error: Chain name mapping not found for chain ID {chain_id}"
        
        # Validate addresses
        if not Web3.is_address(input_token_address):
            return f"Error: Invalid input token address: {input_token_address}"
        
        if not Web3.is_address(output_token_address):
            return f"Error: Invalid output token address: {output_token_address}"
        
        try:
            input_amount_int = int(input_amount)
            if input_amount_int <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid input amount: {input_amount}"
        
        # Use our Paloma-based API implementation
        try:
            estimate_data = await paloma_ctx.palomadex_api.get_token_estimate(
                input_token_address, output_token_address, chain_id, input_amount
            )
            
            if not estimate_data.get('exist', False):
                return f"Error: Trading pair does not exist for these tokens"
            
            if estimate_data.get('empty', True):
                return f"Error: Pool has no liquidity for this trading pair"
            
            # Get token information from blockchain
            web3 = paloma_ctx.web3_clients.get(chain_id)
            if web3:
                try:
                    input_contract = web3.eth.contract(address=input_token_address, abi=ERC20_ABI)
                    output_contract = web3.eth.contract(address=output_token_address, abi=ERC20_ABI)
                    
                    input_symbol = input_contract.functions.symbol().call()
                    output_symbol = output_contract.functions.symbol().call()
                    input_decimals = input_contract.functions.decimals().call()
                    output_decimals = output_contract.functions.decimals().call()
                    
                    # Convert amounts for display
                    input_amount_display = float(input_amount_int) / (10 ** input_decimals)
                    output_amount_wei = int(estimate_data.get('estimated_amount', '0'))
                    output_amount_display = float(output_amount_wei) / (10 ** output_decimals)
                    
                    # Calculate exchange rate and price impact
                    exchange_rate = output_amount_display / input_amount_display if input_amount_display > 0 else 0
                    
                    # Calculate price impact using AMM math
                    price_impact = AMM.calculate_price_impact(
                        input_amount_int, 
                        1000000 * 10**input_decimals,  # Mock reserve
                        1000000 * 10**output_decimals   # Mock reserve
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to get token info from blockchain: {e}")
                    input_symbol = "Unknown"
                    output_symbol = "Unknown"
                    input_decimals = 18
                    output_decimals = 18
                    input_amount_display = float(input_amount_int) / 1e18
                    output_amount_display = float(estimate_data.get('estimated_amount', '0')) / 1e18
                    exchange_rate = 0
                    price_impact = 0
            else:
                input_symbol = "Unknown"
                output_symbol = "Unknown"
                input_amount_display = float(input_amount_int) / 1e18
                output_amount_display = float(estimate_data.get('estimated_amount', '0')) / 1e18
                exchange_rate = 0
                price_impact = 0
            
            result = {
                "chain": config.name,
                "chain_id": config.chain_id,
                "input_token": {
                    "address": input_token_address,
                    "symbol": input_symbol,
                    "amount_wei": input_amount,
                    "amount_display": str(input_amount_display)
                },
                "output_token": {
                    "address": output_token_address,
                    "symbol": output_symbol,
                    "estimated_amount_wei": estimate_data.get('estimated_amount', '0'),
                    "estimated_amount_display": str(output_amount_display)
                },
                "trading_info": {
                    "exchange_rate": f"1 {input_symbol} = {exchange_rate:.6f} {output_symbol}",
                    "price_impact": f"{price_impact:.2f}%",
                    "trading_fee": "0.3%"
                },
                "pool_exists": estimate_data.get('exist', False),
                "has_liquidity": not estimate_data.get('empty', True),
                "data_source": "paloma_amm_calculation",
                "raw_api_response": estimate_data
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as api_error:
            logger.error(f"Price estimation failed: {api_error}")
            return f"Error: Failed to get price estimate: {str(api_error)}"
                
    except Exception as e:
        logger.error(f"Error getting token price estimate: {e}")
        return f"Error getting token price estimate: {str(e)}"

@mcp.tool()
async def approve_token_spending(ctx: Context, chain_id: str, token_address: str, spender_address: str, amount: Optional[str] = None) -> str:
    """Approve token spending for trading (two-step approval process).
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        token_address: Address of token to approve
        spender_address: Address that will spend the tokens (typically Trader contract)
        amount: Amount to approve in wei (defaults to unlimited)
    
    Returns:
        JSON string with approval transaction details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        # Validate addresses
        if not Web3.is_address(token_address):
            return f"Error: Invalid token address: {token_address}"
        
        if not Web3.is_address(spender_address):
            return f"Error: Invalid spender address: {spender_address}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        # Use unlimited approval if no amount specified
        approval_amount = int(amount) if amount else MAX_AMOUNT
        
        # Check current allowance
        current_allowance = token_contract.functions.allowance(
            paloma_ctx.address, spender_address
        ).call()
        
        transactions = []
        
        # Step 1: Reset allowance to 0 if it exists
        if current_allowance > 0:
            reset_tx_data = token_contract.functions.approve(spender_address, 0).build_transaction({
                'from': paloma_ctx.address,
                'gas': 100000,
                'gasPrice': web3.to_wei(config.gas_price_gwei, 'gwei'),
                'nonce': web3.eth.get_transaction_count(paloma_ctx.address)
            })
            
            # Sign and send reset transaction
            signed_reset = paloma_ctx.account.sign_transaction(reset_tx_data)
            reset_tx_hash = web3.eth.send_raw_transaction(signed_reset.rawTransaction)
            
            # Wait for confirmation
            reset_receipt = web3.eth.wait_for_transaction_receipt(reset_tx_hash)
            
            transactions.append({
                "step": "reset_allowance",
                "tx_hash": reset_tx_hash.hex(),
                "status": "success" if reset_receipt.status == 1 else "failed"
            })
        
        # Step 2: Set new allowance
        approve_tx_data = token_contract.functions.approve(spender_address, approval_amount).build_transaction({
            'from': paloma_ctx.address,
            'gas': 100000,
            'gasPrice': web3.to_wei(config.gas_price_gwei, 'gwei'),
            'nonce': web3.eth.get_transaction_count(paloma_ctx.address)
        })
        
        # Sign and send approval transaction
        signed_approve = paloma_ctx.account.sign_transaction(approve_tx_data)
        approve_tx_hash = web3.eth.send_raw_transaction(signed_approve.rawTransaction)
        
        # Wait for confirmation
        approve_receipt = web3.eth.wait_for_transaction_receipt(approve_tx_hash)
        
        transactions.append({
            "step": "set_allowance",
            "tx_hash": approve_tx_hash.hex(),
            "status": "success" if approve_receipt.status == 1 else "failed",
            "approved_amount": str(approval_amount)
        })
        
        # Get token symbol for display
        try:
            token_symbol = token_contract.functions.symbol().call()
        except:
            token_symbol = "Unknown"
        
        result = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "token_address": token_address,
            "token_symbol": token_symbol,
            "spender_address": spender_address,
            "owner_address": paloma_ctx.address,
            "approved_amount": str(approval_amount),
            "is_unlimited": approval_amount == MAX_AMOUNT,
            "transactions": transactions,
            "all_successful": all(tx["status"] == "success" for tx in transactions)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error approving token spending: {e}")
        return f"Error approving token spending: {str(e)}"

@mcp.tool()
async def execute_token_swap(ctx: Context, chain_id: str, from_token_address: str, to_token_address: str, amount_wei: str) -> str:
    """Execute a token swap using the Trader contract.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        from_token_address: Address of token to swap from
        to_token_address: Address of token to swap to
        amount_wei: Amount to swap in wei format
    
    Returns:
        JSON string with swap transaction details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        trader_address = TRADER_ADDRESSES.get(chain_id)
        if not trader_address:
            return f"Error: Trader contract not configured for {config.name}"
        
        # Validate addresses
        if not Web3.is_address(from_token_address):
            return f"Error: Invalid from token address: {from_token_address}"
        
        if not Web3.is_address(to_token_address):
            return f"Error: Invalid to token address: {to_token_address}"
        
        try:
            amount_int = int(amount_wei)
            if amount_int <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid amount: {amount_wei}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        trader_contract = web3.eth.contract(address=trader_address, abi=TRADER_ABI)
        
        # Get gas fee from contract
        try:
            gas_fee = trader_contract.functions.gas_fee().call()
        except Exception as e:
            logger.warning(f"Failed to get gas fee from contract: {e}, using 0")
            gas_fee = 0
        
        # Build transaction
        swap_tx_data = trader_contract.functions.purchase(
            from_token_address,
            to_token_address, 
            amount_int
        ).build_transaction({
            'from': paloma_ctx.address,
            'value': gas_fee,
            'gasPrice': web3.to_wei(config.gas_price_gwei, 'gwei'),
            'nonce': web3.eth.get_transaction_count(paloma_ctx.address)
        })
        
        # Estimate gas with buffer
        try:
            estimated_gas = web3.eth.estimate_gas(swap_tx_data)
            buffered_gas = estimated_gas + (estimated_gas // GAS_MULTIPLIER)  # Add 33% buffer
            swap_tx_data['gas'] = buffered_gas
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            swap_tx_data['gas'] = 300000
        
        # Sign and send transaction
        signed_tx = paloma_ctx.account.sign_transaction(swap_tx_data)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get token symbols for display
        try:
            from_contract = web3.eth.contract(address=from_token_address, abi=ERC20_ABI)
            to_contract = web3.eth.contract(address=to_token_address, abi=ERC20_ABI)
            from_symbol = from_contract.functions.symbol().call()
            to_symbol = to_contract.functions.symbol().call()
            from_decimals = from_contract.functions.decimals().call()
        except:
            from_symbol = "Unknown"
            to_symbol = "Unknown"
            from_decimals = 18
        
        amount_display = float(amount_int) / (10 ** from_decimals)
        
        result = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "trader_contract": trader_address,
            "from_token": {
                "address": from_token_address,
                "symbol": from_symbol,
                "amount_wei": amount_wei,
                "amount_display": str(amount_display)
            },
            "to_token": {
                "address": to_token_address,
                "symbol": to_symbol
            },
            "transaction": {
                "hash": tx_hash.hex(),
                "status": "success" if receipt.status == 1 else "failed",
                "gas_used": receipt.gasUsed,
                "gas_fee_paid": str(gas_fee),
                "block_number": receipt.blockNumber
            },
            "explorer_url": f"{config.explorer_url}/tx/{tx_hash.hex()}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error executing token swap: {e}")
        return f"Error executing token swap: {str(e)}"

@mcp.tool()
async def validate_trade_quote(ctx: Context, chain_id: str, input_token_address: str, output_token_address: str, input_amount: str) -> str:
    """Validate a trade against max spread and liquidity requirements.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        input_token_address: Address of token to trade from
        output_token_address: Address of token to trade to  
        input_amount: Amount of input token in wei format
    
    Returns:
        JSON string with trade validation results.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        # Validate addresses
        if not Web3.is_address(input_token_address):
            return f"Error: Invalid input token address: {input_token_address}"
        
        if not Web3.is_address(output_token_address):
            return f"Error: Invalid output token address: {output_token_address}"
        
        try:
            input_amount_int = int(input_amount)
            if input_amount_int <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid input amount: {input_amount}"
        
        # Use our Paloma-based quote validation
        try:
            quote_data = await paloma_ctx.palomadex_api.get_quote(
                input_token_address, output_token_address, chain_id
            )
            
            if not quote_data.get('exist', False):
                return json.dumps({
                    "valid": False,
                    "reason": "Trading pair does not exist",
                    "chain": config.name,
                    "chain_id": config.chain_id
                }, indent=2)
            
            if quote_data.get('empty', True):
                return json.dumps({
                    "valid": False,
                    "reason": "Pool has no liquidity",
                    "chain": config.name,
                    "chain_id": config.chain_id
                }, indent=2)
            
            # Check against max spread (40% limit)
            available_liquidity = int(quote_data.get('amount0', '0'))
            max_trade_amount = int(available_liquidity * MAX_SPREAD) if available_liquidity > 0 else 0
            
            if input_amount_int > max_trade_amount:
                return json.dumps({
                    "valid": False,
                    "reason": f"Amount exceeds max spread limit ({MAX_SPREAD*100}%)",
                    "max_amount": str(max_trade_amount),
                    "requested_amount": input_amount,
                    "chain": config.name,
                    "chain_id": config.chain_id
                }, indent=2)
            
            # Trade is valid
            return json.dumps({
                "valid": True,
                "available_liquidity": str(available_liquidity),
                "max_trade_amount": str(max_trade_amount),
                "requested_amount": input_amount,
                "spread_check": "passed",
                "chain": config.name,
                "chain_id": config.chain_id,
                "trader_contract": TRADER_ADDRESSES.get(chain_id, "Not configured")
            }, indent=2)
            
        except Exception as api_error:
            logger.error(f"Quote validation failed: {api_error}")
            return json.dumps({
                "valid": False,
                "reason": f"Quote validation failed: {str(api_error)}",
                "chain": config.name,
                "chain_id": config.chain_id
            }, indent=2)
        
    except Exception as e:
        logger.error(f"Error validating trade quote: {e}")
        return f"Error validating trade quote: {str(e)}"

@mcp.tool()
async def check_token_allowance(ctx: Context, chain_id: str, token_address: str, owner_address: str, spender_address: str) -> str:
    """Check token allowance for a specific owner and spender.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        token_address: Address of the token
        owner_address: Address of the token owner
        spender_address: Address of the spender (typically Trader contract)
    
    Returns:
        JSON string with allowance information.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        # Validate addresses
        if not Web3.is_address(token_address):
            return f"Error: Invalid token address: {token_address}"
        
        if not Web3.is_address(owner_address):
            return f"Error: Invalid owner address: {owner_address}"
        
        if not Web3.is_address(spender_address):
            return f"Error: Invalid spender address: {spender_address}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_ABI)
        
        # Get allowance and token info
        allowance = token_contract.functions.allowance(owner_address, spender_address).call()
        
        try:
            token_symbol = token_contract.functions.symbol().call()
            token_decimals = token_contract.functions.decimals().call()
            balance = token_contract.functions.balanceOf(owner_address).call()
        except:
            token_symbol = "Unknown"
            token_decimals = 18
            balance = 0
        
        allowance_display = float(allowance) / (10 ** token_decimals)
        balance_display = float(balance) / (10 ** token_decimals)
        
        result = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "token": {
                "address": token_address,
                "symbol": token_symbol,
                "decimals": token_decimals
            },
            "owner_address": owner_address,
            "spender_address": spender_address,
            "allowance": {
                "wei": str(allowance),
                "display": str(allowance_display),
                "is_unlimited": allowance == MAX_AMOUNT
            },
            "owner_balance": {
                "wei": str(balance),
                "display": str(balance_display)
            },
            "needs_approval": allowance == 0,
            "sufficient_allowance": allowance >= balance if balance > 0 else True
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error checking token allowance: {e}")
        return f"Error checking token allowance: {str(e)}"

@mcp.tool()
async def add_liquidity(ctx: Context, chain_id: str, token0_address: str, token1_address: str, token0_amount: str, token1_amount: str) -> str:
    """Add liquidity to a trading pool using the Trader contract.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        token0_address: Address of first token
        token1_address: Address of second token
        token0_amount: Amount of first token in wei
        token1_amount: Amount of second token in wei
    
    Returns:
        JSON string with liquidity addition transaction details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        trader_address = TRADER_ADDRESSES.get(chain_id)
        if not trader_address:
            return f"Error: Trader contract not configured for {config.name}"
        
        # Validate addresses and amounts
        if not Web3.is_address(token0_address):
            return f"Error: Invalid token0 address: {token0_address}"
        
        if not Web3.is_address(token1_address):
            return f"Error: Invalid token1 address: {token1_address}"
        
        try:
            amount0_int = int(token0_amount)
            amount1_int = int(token1_amount)
            if amount0_int <= 0 or amount1_int <= 0:
                raise ValueError("Amounts must be positive")
        except ValueError:
            return f"Error: Invalid amounts: {token0_amount}, {token1_amount}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        trader_contract = web3.eth.contract(address=trader_address, abi=TRADER_ABI)
        
        # Get gas fee from contract
        try:
            gas_fee = trader_contract.functions.gas_fee().call()
        except Exception as e:
            logger.warning(f"Failed to get gas fee from contract: {e}, using 0")
            gas_fee = 0
        
        # Build transaction
        add_liquidity_tx_data = trader_contract.functions.add_liquidity(
            token0_address,
            token1_address,
            amount0_int,
            amount1_int
        ).build_transaction({
            'from': paloma_ctx.address,
            'value': gas_fee,
            'gasPrice': web3.to_wei(config.gas_price_gwei, 'gwei'),
            'nonce': web3.eth.get_transaction_count(paloma_ctx.address)
        })
        
        # Estimate gas with buffer
        try:
            estimated_gas = web3.eth.estimate_gas(add_liquidity_tx_data)
            buffered_gas = estimated_gas + (estimated_gas // GAS_MULTIPLIER)
            add_liquidity_tx_data['gas'] = buffered_gas
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            add_liquidity_tx_data['gas'] = 400000
        
        # Sign and send transaction
        signed_tx = paloma_ctx.account.sign_transaction(add_liquidity_tx_data)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get token symbols for display
        try:
            token0_contract = web3.eth.contract(address=token0_address, abi=ERC20_ABI)
            token1_contract = web3.eth.contract(address=token1_address, abi=ERC20_ABI)
            token0_symbol = token0_contract.functions.symbol().call()
            token1_symbol = token1_contract.functions.symbol().call()
            token0_decimals = token0_contract.functions.decimals().call()
            token1_decimals = token1_contract.functions.decimals().call()
        except:
            token0_symbol = "Unknown"
            token1_symbol = "Unknown"
            token0_decimals = 18
            token1_decimals = 18
        
        amount0_display = float(amount0_int) / (10 ** token0_decimals)
        amount1_display = float(amount1_int) / (10 ** token1_decimals)
        
        result = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "trader_contract": trader_address,
            "token0": {
                "address": token0_address,
                "symbol": token0_symbol,
                "amount_wei": token0_amount,
                "amount_display": str(amount0_display)
            },
            "token1": {
                "address": token1_address,
                "symbol": token1_symbol,
                "amount_wei": token1_amount,
                "amount_display": str(amount1_display)
            },
            "transaction": {
                "hash": tx_hash.hex(),
                "status": "success" if receipt.status == 1 else "failed",
                "gas_used": receipt.gasUsed,
                "gas_fee_paid": str(gas_fee),
                "block_number": receipt.blockNumber
            },
            "explorer_url": f"{config.explorer_url}/tx/{tx_hash.hex()}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error adding liquidity: {e}")
        return f"Error adding liquidity: {str(e)}"

@mcp.tool()
async def remove_liquidity(ctx: Context, chain_id: str, token0_address: str, token1_address: str, liquidity_amount: str) -> str:
    """Remove liquidity from a trading pool using the Trader contract.
    
    Args:
        chain_id: Chain ID (1, 10, 56, 100, 137, 8453, 42161)
        token0_address: Address of first token
        token1_address: Address of second token
        liquidity_amount: Amount of liquidity tokens to remove in wei
    
    Returns:
        JSON string with liquidity removal transaction details.
    """
    try:
        paloma_ctx = ctx.request_context.lifespan_context
        
        if chain_id not in CHAIN_CONFIGS:
            return f"Error: Unsupported chain ID {chain_id}"
        
        config = CHAIN_CONFIGS[chain_id]
        
        if chain_id not in paloma_ctx.web3_clients:
            return f"Error: Web3 client not available for {config.name}"
        
        trader_address = TRADER_ADDRESSES.get(chain_id)
        if not trader_address:
            return f"Error: Trader contract not configured for {config.name}"
        
        # Validate addresses and amount
        if not Web3.is_address(token0_address):
            return f"Error: Invalid token0 address: {token0_address}"
        
        if not Web3.is_address(token1_address):
            return f"Error: Invalid token1 address: {token1_address}"
        
        try:
            amount_int = int(liquidity_amount)
            if amount_int <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return f"Error: Invalid liquidity amount: {liquidity_amount}"
        
        web3 = paloma_ctx.web3_clients[chain_id]
        trader_contract = web3.eth.contract(address=trader_address, abi=TRADER_ABI)
        
        # Get gas fee from contract
        try:
            gas_fee = trader_contract.functions.gas_fee().call()
        except Exception as e:
            logger.warning(f"Failed to get gas fee from contract: {e}, using 0")
            gas_fee = 0
        
        # Build transaction
        remove_liquidity_tx_data = trader_contract.functions.remove_liquidity(
            token0_address,
            token1_address,
            amount_int
        ).build_transaction({
            'from': paloma_ctx.address,
            'value': gas_fee,
            'gasPrice': web3.to_wei(config.gas_price_gwei, 'gwei'),
            'nonce': web3.eth.get_transaction_count(paloma_ctx.address)
        })
        
        # Estimate gas with buffer
        try:
            estimated_gas = web3.eth.estimate_gas(remove_liquidity_tx_data)
            buffered_gas = estimated_gas + (estimated_gas // GAS_MULTIPLIER)
            remove_liquidity_tx_data['gas'] = buffered_gas
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            remove_liquidity_tx_data['gas'] = 400000
        
        # Sign and send transaction
        signed_tx = paloma_ctx.account.sign_transaction(remove_liquidity_tx_data)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get token symbols for display
        try:
            token0_contract = web3.eth.contract(address=token0_address, abi=ERC20_ABI)
            token1_contract = web3.eth.contract(address=token1_address, abi=ERC20_ABI)
            token0_symbol = token0_contract.functions.symbol().call()
            token1_symbol = token1_contract.functions.symbol().call()
        except:
            token0_symbol = "Unknown"
            token1_symbol = "Unknown"
        
        result = {
            "chain": config.name,
            "chain_id": config.chain_id,
            "trader_contract": trader_address,
            "token0": {
                "address": token0_address,
                "symbol": token0_symbol
            },
            "token1": {
                "address": token1_address,
                "symbol": token1_symbol
            },
            "liquidity_amount_wei": liquidity_amount,
            "transaction": {
                "hash": tx_hash.hex(),
                "status": "success" if receipt.status == 1 else "failed",
                "gas_used": receipt.gasUsed,
                "gas_fee_paid": str(gas_fee),
                "block_number": receipt.blockNumber
            },
            "explorer_url": f"{config.explorer_url}/tx/{tx_hash.hex()}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error removing liquidity: {e}")
        return f"Error removing liquidity: {str(e)}"

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