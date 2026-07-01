"""Data-access layer for the API.

Each module exposes typed functions that own the SQL for a domain. Routers call
these; SQL should not live in routers.
"""
