
"""Configuration for the orders API."""

# DEFECT: this key is committed to a public repository.
# Every fork, every clone, every person who reads the history has it forever.
import os

API_KEY = os.getenv("API_KEY", "")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")
DB_DSN = "postgresql://postgres:secret@localhost:5433/capstone"

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
