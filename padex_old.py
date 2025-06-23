#!/usr/bin/env python3
"""
Paloma DEX MCP Server
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

import httpx
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_abi import encode
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio
import mcp.types as types

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
class EVMChain:
    icon: str
    chainName: str
    chainId: str
    rpc: str
    blockExplorerUrl: str
    hex: str
    nativeCurrency: Dict[str, Any]
    contracts: Dict[str, str]

@dataclass
class Token:
    id: Optional[str] = None
    chainId: Optional[str] = None
    icon: Optional[str] = None
    displayName: str = ""
    symbol: Optional[str] = None
    address: Optional[str] = None
    decimals: int = 18
    balance: str = "0"
    usdAmount: str = "0"
    usdPrice: str = "0"
    amount: str = "0"

@dataclass
class Balance:
    raw: int
    formatted: str

# Chain configurations
CHAINS = {
    ChainID.ETHEREUM_MAIN: EVMChain(
        icon="ethereum.svg",
        chainName="Ethereum",
        chainId="1",
        rpc="https://ethereum.publicnode.com",
        blockExplorerUrl="https://etherscan.io",
        hex="0x1",
        nativeCurrency={"name": "Ethereum", "symbol": "ETH", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_ETH", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_ETH", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_ETH", ""),
            "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "usdt": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "uniswapV3SwapRouter02": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
            "uniswapV3Factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        }
    ),
    ChainID.ARBITRUM_MAIN: EVMChain(
        icon="arbitrum.svg",
        chainName="Arbitrum One",
        chainId="42161",
        rpc="https://arbitrum.drpc.org",
        blockExplorerUrl="https://arbiscan.io",
        hex="0xa4b1",
        nativeCurrency={"name": "Ethereum", "symbol": "ETH", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_ARB", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_ARB", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_ARB", ""),
            "weth": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
            "usdt": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "uniswapV3SwapRouter02": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
            "uniswapV3Factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        }
    ),
    ChainID.OPTIMISM_MAIN: EVMChain(
        icon="optimism.svg",
        chainName="Optimism",
        chainId="10",
        rpc="https://optimism.drpc.org",
        blockExplorerUrl="https://optimistic.etherscan.io",
        hex="0xa",
        nativeCurrency={"name": "Ethereum", "symbol": "ETH", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_OP", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_OP", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_OP", ""),
            "weth": "0x4200000000000000000000000000000000000006",
            "usdt": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
            "uniswapV3SwapRouter02": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
            "uniswapV3Factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        }
    ),
    ChainID.BASE_MAIN: EVMChain(
        icon="base.svg",
        chainName="Base",
        chainId="8453",
        rpc="https://base.drpc.org",
        blockExplorerUrl="https://basescan.org",
        hex="0x2105",
        nativeCurrency={"name": "Ethereum", "symbol": "ETH", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_BASE", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_BASE", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_BASE", ""),
            "weth": "0x4200000000000000000000000000000000000006",
            "usdt": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "uniswapV3SwapRouter02": "0x2626664c2603336E57B271c5C0b26F421741e481",
            "uniswapV3Factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
        }
    ),
    ChainID.BSC_MAIN: EVMChain(
        icon="bnb.svg",
        chainName="BNB Smart Chain",
        chainId="56",
        rpc="https://bsc.drpc.org",
        blockExplorerUrl="https://bscscan.com",
        hex="0x38",
        nativeCurrency={"name": "BNB", "symbol": "BNB", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_BSC", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_BSC", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_BSC", ""),
            "weth": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
            "usdt": "0x55d398326f99059fF775485246999027B3197955",
            "uniswapV3SwapRouter02": "0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2",
            "uniswapV3Factory": "0xdB1d10011AD0Ff90774D0C6Bb92e5C5c8b4461F7"
        }
    ),
    ChainID.POLYGON_MAIN: EVMChain(
        icon="polygon.svg",
        chainName="Polygon",
        chainId="137",
        rpc="https://polygon.drpc.org",
        blockExplorerUrl="https://polygonscan.com",
        hex="0x89",
        nativeCurrency={"name": "MATIC", "symbol": "MATIC", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_MATIC", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_MATIC", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_MATIC", ""),
            "weth": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
            "usdt": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            "uniswapV3SwapRouter02": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
            "uniswapV3Factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        }
    ),
    ChainID.GNOSIS_MAIN: EVMChain(
        icon="gnosis.svg",
        chainName="Gnosis",
        chainId="100",
        rpc="https://gnosis.drpc.org",
        blockExplorerUrl="https://gnosisscan.io",
        hex="0x64",
        nativeCurrency={"name": "xDAI", "symbol": "xDAI", "decimals": 18},
        contracts={
            "pusd": os.getenv("PUSD_TOKEN_GNOSIS", ""),
            "pusdConnector": os.getenv("PUSD_CONNECTOR_GNOSIS", ""),
            "etfConnector": os.getenv("ETF_CONNECTOR_GNOSIS", ""),
            "weth": "0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d",
            "usdt": "0x4ECaBa5870353805a9F068101A40E0f32ed605C6",
            "uniswapV3SwapRouter02": "0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2",
            "uniswapV3Factory": "0xf78031CBCA409F2FB6876BDFDBc1b2df24cF9bEf"
        }
    ),
}

# Contract ABIs (simplified for key functions)
PUSD_CONNECTOR_ABI = [
    {
        "name": "purchase",
        "type": "function",
        "inputs": [
            {"name": "path", "type": "bytes"},
            {"name": "amount", "type": "uint256"},
            {"name": "min_amount", "type": "uint256"}
        ],
        "outputs": [],
        "stateMutability": "payable"
    },
    {
        "name": "withdraw",
        "type": "function",
        "inputs": [{"name": "amount", "type": "uint256"}],
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

ERC20_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable"
    },
    {
        "name": "allowance",
        "type": "function",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view"
    }
]

class PalomaDEXServer:
    def __init__(self):
        self.server = Server("paloma-dex")
        self.private_key = os.getenv("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("PRIVATE_KEY environment variable is required")
        
        self.account = Account.from_key(self.private_key)
        self.address = self.account.address
        
        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Web3 instances for each chain
        self.web3_instances = {}
        for chain_id, chain in CHAINS.items():
            self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(chain.rpc))
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="buy_token",
                    description="Buy ETF tokens or PUSD using any input token",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "Chain ID (1, 10, 56, 137, 8453, 42161, 100)",
                                "enum": ["1", "10", "56", "137", "8453", "42161", "100"]
                            },
                            "input_token_address": {
                                "type": "string",
                                "description": "Address of token to spend (use 'native' for ETH/BNB/MATIC/xDAI)"
                            },
                            "output_token_address": {
                                "type": "string", 
                                "description": "Address of token to buy (ETF token or PUSD)"
                            },
                            "input_amount": {
                                "type": "string",
                                "description": "Amount of input token to spend (in token units, e.g. '1.5')"
                            },
                            "slippage": {
                                "type": "number",
                                "description": "Slippage tolerance as percentage (default: 2.0)",
                                "default": 2.0
                            }
                        },
                        "required": ["chain_id", "input_token_address", "output_token_address", "input_amount"]
                    }
                ),
                Tool(
                    name="sell_token",
                    description="Sell ETF tokens or PUSD back to other tokens",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "Chain ID (1, 10, 56, 137, 8453, 42161, 100)",
                                "enum": ["1", "10", "56", "137", "8453", "42161", "100"]
                            },
                            "token_address": {
                                "type": "string",
                                "description": "Address of ETF token or PUSD to sell"
                            },
                            "amount": {
                                "type": "string",
                                "description": "Amount to sell (in token units, e.g. '100.0')"
                            }
                        },
                        "required": ["chain_id", "token_address", "amount"]
                    }
                ),
                Tool(
                    name="get_balance",
                    description="Get token balances for the wallet across chains",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "Chain ID (1, 10, 56, 137, 8453, 42161, 100). If not provided, returns balances for all chains",
                                "enum": ["1", "10", "56", "137", "8453", "42161", "100"]
                            },
                            "token_address": {
                                "type": "string",
                                "description": "Specific token address to check. If not provided, returns all major token balances"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_price",
                    description="Get current token prices",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain_id": {
                                "type": "string",
                                "description": "Chain ID (1, 10, 56, 137, 8453, 42161, 100)",
                                "enum": ["1", "10", "56", "137", "8453", "42161", "100"]
                            },
                            "token_address": {
                                "type": "string",
                                "description": "Token address to get price for"
                            }
                        },
                        "required": ["chain_id", "token_address"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "buy_token":
                    result = await self.buy_token(**arguments)
                elif name == "sell_token":
                    result = await self.sell_token(**arguments)
                elif name == "get_balance":
                    result = await self.get_balance(**arguments)
                elif name == "get_price":
                    result = await self.get_price(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def buy_token(self, chain_id: str, input_token_address: str, 
                       output_token_address: str, input_amount: str, 
                       slippage: float = 2.0) -> Dict[str, Any]:
        """Buy ETF tokens or PUSD using any input token"""
        try:
            chain = CHAINS[ChainID(chain_id)]
            web3 = self.web3_instances[ChainID(chain_id)]
            
            # Convert amount to wei
            if input_token_address.lower() == "native":
                input_amount_wei = web3.to_wei(input_amount, 'ether')
                input_token_decimals = 18
            else:
                token_contract = web3.eth.contract(
                    address=Web3.to_checksum_address(input_token_address),
                    abi=ERC20_ABI
                )
                input_token_decimals = token_contract.functions.decimals().call()
                input_amount_wei = int(Decimal(input_amount) * (10 ** input_token_decimals))
            
            # Check if output token is PUSD
            is_pusd = output_token_address.lower() == chain.contracts["pusd"].lower()
            
            if is_pusd:
                return await self._buy_pusd(chain_id, input_token_address, input_amount_wei, slippage)
            else:
                return await self._buy_etf(chain_id, input_token_address, input_amount_wei, 
                                         output_token_address, slippage)
            
        except Exception as e:
            logger.error(f"Error in buy_token: {e}")
            raise
    
    async def sell_token(self, chain_id: str, token_address: str, amount: str) -> Dict[str, Any]:
        """Sell ETF tokens or PUSD"""
        try:
            chain = CHAINS[ChainID(chain_id)]
            web3 = self.web3_instances[ChainID(chain_id)]
            
            # Get token contract to determine decimals
            token_contract = web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            decimals = token_contract.functions.decimals().call()
            amount_wei = int(Decimal(amount) * (10 ** decimals))
            
            # Check if token is PUSD
            is_pusd = token_address.lower() == chain.contracts["pusd"].lower()
            
            if is_pusd:
                return await self._sell_pusd(chain_id, amount_wei)
            else:
                return await self._sell_etf(chain_id, token_address, amount_wei)
                
        except Exception as e:
            logger.error(f"Error in sell_token: {e}")
            raise
    
    async def get_balance(self, chain_id: Optional[str] = None, 
                         token_address: Optional[str] = None) -> Dict[str, Any]:
        """Get token balances"""
        try:
            balances = {}
            
            chains_to_check = [ChainID(chain_id)] if chain_id else list(CHAINS.keys())
            
            for cid in chains_to_check:
                chain = CHAINS[cid]
                web3 = self.web3_instances[cid]
                chain_balances = {}
                
                # Native token balance
                native_balance = web3.eth.get_balance(self.address)
                chain_balances["native"] = {
                    "symbol": chain.nativeCurrency["symbol"],
                    "balance": web3.from_wei(native_balance, 'ether'),
                    "raw": str(native_balance)
                }
                
                # PUSD balance
                if chain.contracts["pusd"]:
                    try:
                        pusd_contract = web3.eth.contract(
                            address=Web3.to_checksum_address(chain.contracts["pusd"]),
                            abi=ERC20_ABI
                        )
                        balance = pusd_contract.functions.balanceOf(self.address).call()
                        decimals = pusd_contract.functions.decimals().call()
                        chain_balances["pusd"] = {
                            "address": chain.contracts["pusd"],
                            "balance": str(Decimal(balance) / (10 ** decimals)),
                            "raw": str(balance)
                        }
                    except Exception as e:
                        logger.warning(f"Could not get PUSD balance on {chain.chainName}: {e}")
                
                # USDT balance
                if chain.contracts["usdt"]:
                    try:
                        usdt_contract = web3.eth.contract(
                            address=Web3.to_checksum_address(chain.contracts["usdt"]),
                            abi=ERC20_ABI
                        )
                        balance = usdt_contract.functions.balanceOf(self.address).call()
                        decimals = usdt_contract.functions.decimals().call()
                        chain_balances["usdt"] = {
                            "address": chain.contracts["usdt"],
                            "balance": str(Decimal(balance) / (10 ** decimals)),
                            "raw": str(balance)
                        }
                    except Exception as e:
                        logger.warning(f"Could not get USDT balance on {chain.chainName}: {e}")
                
                # Specific token balance if requested
                if token_address:
                    try:
                        token_contract = web3.eth.contract(
                            address=Web3.to_checksum_address(token_address),
                            abi=ERC20_ABI
                        )
                        balance = token_contract.functions.balanceOf(self.address).call()
                        decimals = token_contract.functions.decimals().call()
                        chain_balances["requested_token"] = {
                            "address": token_address,
                            "balance": str(Decimal(balance) / (10 ** decimals)),
                            "raw": str(balance)
                        }
                    except Exception as e:
                        logger.warning(f"Could not get token balance for {token_address}: {e}")
                
                balances[chain.chainName] = chain_balances
            
            return {
                "wallet_address": self.address,
                "balances": balances
            }
            
        except Exception as e:
            logger.error(f"Error in get_balance: {e}")
            raise
    
    async def get_price(self, chain_id: str, token_address: str) -> Dict[str, Any]:
        """Get token price"""
        try:
            chain = CHAINS[ChainID(chain_id)]
            
            # Try PalomaDEX API first for custom tokens
            try:
                chain_name = chain.chainName.lower().replace(" ", "")
                url = f"https://api.palomadex.com/etfapi/v1/customindexprice"
                params = {
                    "chain_id": chain_name,
                    "token_evm_address": token_address
                }
                
                response = await self.http_client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "token_address": token_address,
                        "chain_id": chain_id,
                        "buy_price": data.get("buy_price"),
                        "sell_price": data.get("sell_price"),
                        "source": "palomadex"
                    }
            except Exception as e:
                logger.warning(f"PalomaDEX API failed: {e}")
            
            # Fallback to Moralis or other price APIs would go here
            return {
                "token_address": token_address,
                "chain_id": chain_id,
                "error": "Price data not available",
                "source": "none"
            }
            
        except Exception as e:
            logger.error(f"Error in get_price: {e}")
            raise
    
    async def _buy_pusd(self, chain_id: str, input_token_address: str, 
                       input_amount_wei: int, slippage: float) -> Dict[str, Any]:
        """Buy PUSD using input token"""
        chain = CHAINS[ChainID(chain_id)]
        web3 = self.web3_instances[ChainID(chain_id)]
        
        # Get swap path (simplified - would need actual Uniswap integration)
        path = await self._get_swap_path(chain_id, input_token_address, chain.contracts["pusd"], input_amount_wei)
        
        # Calculate minimum amount with slippage
        min_amount = int(input_amount_wei * (100 - slippage) / 100)
        
        connector = web3.eth.contract(
            address=Web3.to_checksum_address(chain.contracts["pusdConnector"]),
            abi=PUSD_CONNECTOR_ABI
        )
        
        # Approve token if not native
        if input_token_address.lower() != "native":
            await self._approve_token(chain_id, input_token_address, 
                                    chain.contracts["pusdConnector"], input_amount_wei)
        
        # Get gas fee
        gas_fee = connector.functions.gas_fee().call()
        
        # Build transaction
        tx_value = gas_fee
        if input_token_address.lower() == "native":
            tx_value += input_amount_wei
        
        transaction = connector.functions.purchase(
            path.encode() if isinstance(path, str) else path,
            input_amount_wei,
            min_amount
        ).build_transaction({
            'from': self.address,
            'value': tx_value,
            'gas': 500000,  # Estimated
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(self.address)
        })
        
        # Sign and send transaction
        signed_txn = web3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for confirmation
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        return {
            "success": receipt.status == 1,
            "transaction_hash": tx_hash.hex(),
            "gas_used": receipt.gasUsed,
            "block_number": receipt.blockNumber,
            "operation": "buy_pusd",
            "chain_id": chain_id
        }
    
    async def _buy_etf(self, chain_id: str, input_token_address: str, 
                      input_amount_wei: int, etf_token_address: str, slippage: float) -> Dict[str, Any]:
        """Buy ETF token using input token"""
        # This would be implemented similar to _buy_pusd but using ETF connector
        # For brevity, returning placeholder
        return {
            "error": "ETF buying not fully implemented yet",
            "operation": "buy_etf",
            "chain_id": chain_id
        }
    
    async def _sell_pusd(self, chain_id: str, amount_wei: int) -> Dict[str, Any]:
        """Sell PUSD tokens"""
        chain = CHAINS[ChainID(chain_id)]
        web3 = self.web3_instances[ChainID(chain_id)]
        
        # Approve PUSD spending
        await self._approve_token(chain_id, chain.contracts["pusd"], 
                                chain.contracts["pusdConnector"], amount_wei)
        
        connector = web3.eth.contract(
            address=Web3.to_checksum_address(chain.contracts["pusdConnector"]),
            abi=PUSD_CONNECTOR_ABI
        )
        
        # Get gas fee
        gas_fee = connector.functions.gas_fee().call()
        
        # Build transaction
        transaction = connector.functions.withdraw(amount_wei).build_transaction({
            'from': self.address,
            'value': gas_fee,
            'gas': 300000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(self.address)
        })
        
        # Sign and send
        signed_txn = web3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        return {
            "success": receipt.status == 1,
            "transaction_hash": tx_hash.hex(),
            "gas_used": receipt.gasUsed,
            "block_number": receipt.blockNumber,
            "operation": "sell_pusd",
            "chain_id": chain_id
        }
    
    async def _sell_etf(self, chain_id: str, token_address: str, amount_wei: int) -> Dict[str, Any]:
        """Sell ETF tokens"""
        # Placeholder for ETF selling implementation
        return {
            "error": "ETF selling not fully implemented yet",
            "operation": "sell_etf",
            "chain_id": chain_id
        }
    
    async def _approve_token(self, chain_id: str, token_address: str, 
                           spender: str, amount: int) -> bool:
        """Approve token spending"""
        web3 = self.web3_instances[ChainID(chain_id)]
        
        token_contract = web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        # Check current allowance
        current_allowance = token_contract.functions.allowance(self.address, spender).call()
        
        if current_allowance >= amount:
            return True
        
        # Approve spending
        transaction = token_contract.functions.approve(spender, amount).build_transaction({
            'from': self.address,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'nonce': web3.eth.get_transaction_count(self.address)
        })
        
        signed_txn = web3.eth.account.sign_transaction(transaction, self.private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        return receipt.status == 1
    
    async def _get_swap_path(self, chain_id: str, from_token: str, to_token: str, amount: int) -> bytes:
        """Get swap path for Uniswap routing (simplified)"""
        # This would integrate with Uniswap V3 quoter to get optimal path
        # For now, returning direct path
        if from_token.lower() == "native":
            chain = CHAINS[ChainID(chain_id)]
            from_token = chain.contracts["weth"]
        
        # Direct path: from_token -> to_token
        path = encode(['address', 'uint24', 'address'], 
                     [Web3.to_checksum_address(from_token), 3000, Web3.to_checksum_address(to_token)])
        return path

async def main():
    """Main entry point"""
    server = PalomaDEXServer()
    
    # Run the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="paloma-dex",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())