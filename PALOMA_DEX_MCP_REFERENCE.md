# PalomaDEX MCP Server Reference Documentation

This document provides comprehensive reference information for implementing an MCP server that replicates the buy/sell token functionality of PalomaDEX.

## Overview

PalomaDEX is a cross-chain DEX built on Paloma blockchain that supports trading across 7 EVM chains (Ethereum, Arbitrum, Optimism, Base, BSC, Polygon, Gnosis). The buy/sell token functionality allows users to:

- **Buy**: Exchange any token for ETF tokens or PUSD using cross-chain routing
- **Sell**: Exchange ETF tokens or PUSD back to other tokens (typically USDT)

## Architecture Components

### 1. Chain Configuration

**Supported Chains:**
```typescript
enum ChainID {
  ETHEREUM_MAIN = "1",
  OPTIMISM_MAIN = "10", 
  BSC_MAIN = "56",
  POLYGON_MAIN = "137",
  BASE_MAIN = "8453",
  ARBITRUM_MAIN = "42161",
  GNOSIS_MAIN = "100"
}
```

**Chain Data Structure:**
```typescript
interface EVMChain {
  icon: string;
  chainName: string;
  chainId: string;
  rpc: string;
  blockExplorerUrl: string;
  hex: string;
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
}
```

### 2. Token Interfaces

**Token Structure:**
```typescript
interface IToken {
  id?: string;
  chainId?: string | number;
  icon?: string;
  displayName: string;
  symbol: string | null;
  address: string | null;
  decimals?: number;
  balance?: string;
  usdAmount?: string;
  usdPrice?: string;
  amount?: string;
}

interface IBalance {
  raw: BigNumber;
  format: string;
}
```

### 3. Contract Addresses

**Environment Variables Required:**
- `PUSD_CONNECTOR_[CHAIN]` - PUSD connector contract addresses
- `PUSD_TOKEN_[CHAIN]` - PUSD token addresses
- `ETF_CONNECTOR_[CHAIN]` - ETF connector contract addresses
- `MORALIS_SERVICE_API_KEY` - For blockchain data

**Key Contract Addresses per Chain:**
```typescript
// Example for Ethereum mainnet
{
  pusd: process.env.PUSD_TOKEN_ETH,
  pusdConnector: process.env.PUSD_CONNECTOR_ETH,
  etfConnector: process.env.ETF_CONNECTOR_ETH,
  weth: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
  usdt: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
  uniswapV3SwapRouter02: "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
  uniswapV3Factory: "0x1F98431c8aD98523631AE4a59f267346ea31F984"
}
```

## Core Trading Functions

### 1. Buy Tokens Flow

**Process:**
1. **Token Selection**: User selects input token (from their balance) and output token (ETF/PUSD)
2. **Price Estimation**: Get swap path via Uniswap and custom pricing API
3. **Approval**: Approve input token spending to appropriate connector
4. **Transaction**: Execute buy via connector contract

**Key Functions:**
```typescript
// PUSD Buy
async function buyPusd(
  fromToken: IToken,
  fromTokenAmount: IBalance,
  minAmount: IBalance,
  path: string
) {
  // 1. Approve fromToken to pusdConnector
  // 2. Call pusdConnector.purchase(path, amount, minAmount)
  // 3. Handle gas fees and transaction
}

// ETF Buy
async function buyEtf(
  etfToken: IToken,
  etfAmount: IBalance,
  fromToken: IToken,
  fromTokenAmount: IBalance,
  recipient: string,
  path: string
) {
  // 1. Approve fromToken to etfConnector
  // 2. Call etfConnector.buy(etfToken, etfAmount, fromAmount, recipient, path, 0)
  // 3. Handle gas fees and transaction
}
```

### 2. Sell Tokens Flow

**Process:**
1. **Token Selection**: User selects token to sell (from their ETF/PUSD balance)
2. **Price Calculation**: Calculate output amount using custom pricing
3. **Approval**: Approve sell token to appropriate connector
4. **Transaction**: Execute sell via connector contract

**Key Functions:**
```typescript
// PUSD Sell
async function sellPusd(pusdAddress: string, amount: IBalance) {
  // 1. Approve PUSD to pusdConnector
  // 2. Call pusdConnector.withdraw(amount)
  // 3. Handle gas fees and transaction
}

// ETF Sell
async function sellEtf(etfAddress: string, amount: IBalance, recipient: string) {
  // 1. Approve ETF token to etfConnector
  // 2. Call etfConnector.sell(etfAddress, amount, 0, recipient)
  // 3. Handle gas fees and transaction
}
```

## Contract ABIs

### PUSD Connector ABI (Key Functions)
```json
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
```

### ETF Connector ABI (Key Functions)
```json
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
```

## API Endpoints

### PalomaDEX API
**Base URL**: `https://api.palomadex.com/etfapi/v1`

**Endpoints:**
```typescript
// Get available ETF tokens
GET /etf?chain_id={chain_name}
// Returns: Array of token objects with evm addresses

// Get custom token pricing
GET /customindexprice?chain_id={chain_name}&token_evm_address={address}
// Returns: { buy_price: string, sell_price: string }

// Get token price by symbol
GET /price?symbol={symbol}
// Returns: Price data
```

### Moralis API Integration
**Functions Required:**
```typescript
// Get user token balances
async getUserTokens(userAddress: string, chainId: string): Promise<IToken[]>

// Get specific token balances
async getMyTokensForAddresses(
  wallet: string, 
  chainId: string, 
  tokenAddresses: string[]
): Promise<any[]>

// Get native token balance
async getNativeTokenBalance(wallet: string, chainId: string): Promise<string>

// Get token prices
async getMultipleTokenPrices(
  tokenAddresses: string[], 
  chainId: string
): Promise<any[]>
```

## Web3 Integration Requirements

### 1. Wallet Connection
**Supported Wallets:**
- MetaMask
- WalletConnect
- Coinbase Wallet
- Ledger
- Trezor
- Frame

**Connection Management:**
```typescript
interface WalletState {
  account: string;
  providerName: string;
  provider: any;
  network: string;
}

// Required functions
async connectWallet(): Promise<void>
async disconnectWallet(): Promise<void>
async requestSwitchNetwork(chainId: string): Promise<boolean>
```

### 2. Contract Interaction
**Transaction Pattern:**
```typescript
async function executeContractCall(
  contractAddress: string,
  abi: any[],
  functionName: string,
  args: any[],
  value?: string
) {
  // 1. Get provider and signer
  // 2. Create contract instance
  // 3. Estimate gas with 33% buffer
  // 4. Execute transaction
  // 5. Wait for confirmation
  // 6. Return success/error status
}
```

### 3. Token Operations
**Required Functions:**
```typescript
// Check token allowance
async getTokenAllowance(
  tokenAddress: string,
  owner: string,
  spender: string
): Promise<string>

// Approve token spending
async tokenApprove(
  tokenAddress: string,
  owner: string,
  spender: string,
  amount: string
): Promise<boolean>
```

## Uniswap Integration

### Path Generation
**Required for PUSD purchases:**
```typescript
// Generate swap path for token routing
async getSwapPath(
  fromToken: IToken,
  toToken: IToken,
  amount: IBalance,
  slippage: number,
  deadline: number,
  chainId: string,
  exactIn: boolean,
  isQuote: boolean
): Promise<any>

// Get quote amount from path
function getQuoteAmount(path: any): IBalance | null

// Convert path for V3 router
function getSwapPathForV3(path: any, toToken: IToken): { path: string }
```

## Transaction Flow States

**UI State Management:**
```typescript
enum AddLiquidity {
  SelectToken = "Select Token",
  EnterAmount = "Enter Amount", 
  Insufficient = "Insufficient Balance",
  Swap = "Swap",
  IsLoading = "Loading..."
}

enum TokenSwapStep {
  Swap = "swap",
  ConfirmApprove = "confirm-approve",
  ConfirmTransaction = "confirm-transaction"
}
```

## Error Handling

**Common Error Patterns:**
```typescript
// Transaction error parsing
function txErrorMessage(error: any): string {
  // Parse revert reasons, gas estimation errors, etc.
  // Return user-friendly error messages
}

// Retry logic for failed API calls
async function withRetry<T>(
  operation: () => Promise<T>, 
  maxRetries: number = 3
): Promise<T>
```

## Gas Fee Management

**Gas Estimation:**
```typescript
// Add 33% buffer to estimated gas
const GAS_MULTIPLIER = 3; // Divide by this for 33% buffer
estimatedGas = estimatedGas.add(estimatedGas.div(GAS_MULTIPLIER));

// Get protocol gas fees
async function getGasFee(contractAddress: string): Promise<string> {
  // Call gas_fee() function on connector contracts
}
```

## Data Validation

**Input Validation:**
```typescript
// Validate addresses
function isSameContract(address1?: string, address2?: string): boolean

// Balance comparisons
function validateSufficientBalance(
  inputAmount: IBalance, 
  tokenBalance: string
): boolean

// Amount formatting
function formatNumber(
  value: string | number, 
  minDecimals: number = 2, 
  maxDecimals: number = 4
): string
```

## Environment Configuration

**Required Environment Variables:**
```bash
# Contract addresses for each chain
PUSD_CONNECTOR_ETH=0x...
PUSD_TOKEN_ETH=0x...
ETF_CONNECTOR_ETH=0x...

PUSD_CONNECTOR_ARB=0x...
PUSD_TOKEN_ARB=0x...
ETF_CONNECTOR_ARB=0x...

# Continue for all 7 chains...

# API keys
MORALIS_SERVICE_API_KEY=your_key_here
```

## Implementation Notes

1. **Cross-chain Operations**: All trades are cross-chain via Paloma blockchain orchestration
2. **Gas Management**: Both gas estimation and protocol fees must be handled
3. **Price Calculation**: Use both Uniswap routing and custom pricing APIs
4. **Token Approval**: Always check and handle token approvals before trades
5. **Error Handling**: Implement comprehensive error handling for transaction failures
6. **State Management**: Track transaction states for proper UI feedback
7. **Security**: Never expose private keys or commit secrets to repositories

## Testing Considerations

- Test with multiple wallet providers
- Verify gas estimation accuracy
- Test approval flows for different tokens
- Validate error handling for network issues
- Test cross-chain functionality across all supported chains
- Verify price calculation accuracy

This reference provides the foundation needed to implement a comprehensive MCP server that replicates PalomaDEX's buy/sell token functionality across all supported chains.