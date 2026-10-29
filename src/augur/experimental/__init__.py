"""Experimental, library-only modules.

The modules in this subpackage (``accounting``, ``capital_allocation``,
``debate_engine``, ``relative_val``, ``portfolio_risk``) are not wired into
any product path: the CLI, dashboard and MCP server do not call them. They
have unit tests but are untested in the product path, and their API may
change or be removed without a deprecation cycle. Import them explicitly,
e.g. ``from augur.experimental.accounting import AccountingReviewer``.
"""
