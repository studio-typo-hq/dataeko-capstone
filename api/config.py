"""Configuration for the orders API."""
import os
# DEFECT: this key is committed to a public repository.
# Every fork, every clone, every person who reads the history has it forever.
API_KEY = os.environ.get("API_KEY", "")

ADMIN_KEY = "dataeko-capstone-admin"

DB_DSN = "postgresql://postgres:password@localhost:5434/capstone"

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
