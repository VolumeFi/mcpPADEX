# MCP Python SDK Reference

This document provides reference information for the Model Context Protocol (MCP) Python SDK based on the official repository at https://github.com/modelcontextprotocol/python-sdk

## Overview

The MCP Python SDK is a powerful library that enables developers to build MCP servers and clients with Python. It provides high-level abstractions for creating standardized LLM integrations.

## Installation

### Using uv (Recommended)
```bash
uv add mcp
```

### Using pip
```bash
pip install mcp
```

## Core Concepts

### Servers
MCP servers can expose four main types of capabilities:

1. **Resources**: Data retrieval endpoints that provide information
2. **Tools**: Functional endpoints that can perform actions with side effects
3. **Prompts**: Interaction templates for common use cases
4. **Completions**: Intelligent suggestions and auto-completion

### FastMCP
FastMCP is a high-level server framework that simplifies MCP server creation:

```python
from mcp.server.fastmcp import FastMCP

# Create a new MCP server
mcp = FastMCP("My Server Name")
```

## Quick Start Example

```python
from mcp.server.fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("Demo")

# Define a tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

# Define a resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting for someone"""
    return f"Hello, {name}!"

# Run the server
if __name__ == "__main__":
    mcp.run()
```

## Key Features

### Tools
Tools are functions that can be called by MCP clients to perform actions:

```python
@mcp.tool()
def my_tool(param1: str, param2: int) -> str:
    """Tool description here"""
    # Tool implementation
    return result
```

### Resources
Resources provide access to data and information:

```python
@mcp.resource("resource://pattern/{variable}")
def get_resource(variable: str) -> str:
    """Resource description"""
    # Resource implementation
    return data
```

### Prompts
Prompts are templates for common interactions:

```python
@mcp.prompt()
def my_prompt(context: str) -> str:
    """Prompt description"""
    return f"Based on {context}, please..."
```

### Async Support
The SDK supports asynchronous operations:

```python
@mcp.tool()
async def async_tool(param: str) -> str:
    """Async tool example"""
    await some_async_operation()
    return result
```

## Server Configuration

### Transport Options
MCP servers can use different transport mechanisms:

- **STDIO**: Standard input/output (most common)
- **HTTP**: RESTful API endpoints
- **WebSocket**: Real-time bidirectional communication

### Server Lifecycle
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Server Name")

# Configure server capabilities
@mcp.tool()
def example_tool():
    pass

# Run the server with specific transport
if __name__ == "__main__":
    mcp.run(transport="stdio")  # or "http", "websocket"
```

## Advanced Features

### Error Handling
```python
from mcp.server.exceptions import McpError

@mcp.tool()
def risky_operation(input: str) -> str:
    try:
        # Risky operation
        result = perform_operation(input)
        return result
    except Exception as e:
        raise McpError(f"Operation failed: {str(e)}")
```

### Context Management
```python
@mcp.tool()
def context_aware_tool(request_context) -> str:
    """Tool that uses request context"""
    # Access client information, session data, etc.
    return f"Processing for client: {request_context.client_info}"
```

### Resource Templates
```python
# Resource with multiple parameters
@mcp.resource("data://{category}/{item_id}")
def get_data_item(category: str, item_id: str) -> dict:
    """Get specific data item"""
    return {
        "category": category,
        "id": item_id,
        "data": fetch_data(category, item_id)
    }
```

## Best Practices

### 1. Tool Design
- Use clear, descriptive function names
- Provide comprehensive docstrings
- Validate input parameters
- Return structured data when possible

### 2. Resource Management
- Use meaningful URI patterns
- Implement proper caching where appropriate
- Handle resource not found scenarios gracefully

### 3. Error Handling
- Catch and wrap exceptions appropriately
- Provide helpful error messages
- Use proper HTTP status codes for web transports

### 4. Performance
- Use async/await for I/O operations
- Implement connection pooling for external services
- Consider rate limiting for resource-intensive operations

## Integration Examples

### Database Integration
```python
@mcp.resource("db://table/{table_name}")
async def get_table_data(table_name: str) -> list:
    """Get data from database table"""
    async with database.connection() as conn:
        return await conn.fetch_all(f"SELECT * FROM {table_name}")

@mcp.tool()
async def insert_record(table: str, data: dict) -> str:
    """Insert new record into database"""
    async with database.connection() as conn:
        await conn.execute(f"INSERT INTO {table} VALUES (...)")
        return "Record inserted successfully"
```

### API Integration
```python
import httpx

@mcp.tool()
async def fetch_external_data(endpoint: str) -> dict:
    """Fetch data from external API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        response.raise_for_status()
        return response.json()
```

### File System Access
```python
import os
from pathlib import Path

@mcp.resource("file://{file_path}")
def read_file(file_path: str) -> str:
    """Read file contents"""
    path = Path(file_path)
    if not path.exists():
        raise McpError(f"File not found: {file_path}")
    return path.read_text()

@mcp.tool()
def write_file(file_path: str, content: str) -> str:
    """Write content to file"""
    path = Path(file_path)
    path.write_text(content)
    return f"File written: {file_path}"
```

## Testing

### Unit Testing
```python
import pytest
from mcp.server.fastmcp import FastMCP

def test_tool():
    mcp = FastMCP("Test Server")
    
    @mcp.tool()
    def test_function(x: int) -> int:
        return x * 2
    
    # Test the tool directly
    result = test_function(5)
    assert result == 10
```

### Integration Testing
```python
import asyncio
from mcp.client import Client

async def test_server_integration():
    # Test full server integration
    client = Client("test://server")
    result = await client.call_tool("my_tool", {"param": "value"})
    assert result["success"] == True
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "server.py"]
```

### Production Considerations
- Use proper logging configuration
- Implement health checks
- Set up monitoring and alerting
- Configure proper security measures
- Use environment variables for configuration

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure MCP SDK is properly installed
2. **Connection Issues**: Check transport configuration
3. **Tool Not Found**: Verify tool registration and naming
4. **Resource Access**: Check URI patterns and permissions

### Debugging
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# The SDK will provide detailed logs about:
# - Client connections
# - Tool calls
# - Resource requests
# - Error conditions
```

## Community and Support

- **GitHub Repository**: https://github.com/modelcontextprotocol/python-sdk
- **Documentation**: Official MCP documentation
- **Issues**: Report bugs and feature requests on GitHub
- **Contributing**: Follow the contribution guidelines in the repository

---

*This reference is based on the official MCP Python SDK and is subject to updates as the SDK evolves.*