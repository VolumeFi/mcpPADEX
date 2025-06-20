# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is mcppadex, a Python project that appears to be in early development. The project uses uv for dependency management and includes dependencies for HTTP requests (httpx) and MCP (Model Context Protocol) CLI tools.

## Development Commands

The project uses uv for package management:

- Install dependencies: `uv sync`
- Run the main application: `uv run python main.py`
- Run Python scripts: `uv run python <script_name>.py`

## Architecture

- `main.py`: Entry point with basic "Hello World" functionality
- `padex.py`: Currently empty, likely intended for core functionality
- `pyproject.toml`: Project configuration with dependencies on httpx and mcp[cli]

## Dependencies

- httpx: HTTP client library
- mcp[cli]: Model Context Protocol CLI tools

The project requires Python 3.12 or higher.