"""Augur MCP Server — stdio entry point for desktop MCP clients.

Use with Hermes Studio / Claude Desktop / mcporter / any stdio MCP client:
    augur-mcp
"""
from augur.mcp_server import run_server

if __name__ == "__main__":
    run_server()
