"""
Configuration module for Caught U! Red Agent
Loads environment variables and provides config constants
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://xxxxxxxx.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password_here")

# Gemini LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
GEMINI_MODEL = "gemini-1.5-pro"

# NVD Configuration (for demo, use pre-cached data)
NVD_API_KEY = os.getenv("NVD_API_KEY", "")
USE_CACHED_NVD = os.getenv("USE_CACHED_NVD", "true").lower() == "true"
NVD_CACHE_PATH = os.getenv("NVD_CACHE_PATH", "data/nvd_cache.json")

# Graph Configuration
SIMULATION_GRAPH = "sim"
PRODUCTION_GRAPH = "prod"

# Red Agent Configuration
MAX_ATTACK_VECTORS = 5
CRITICALITY_THRESHOLD = "High"  # Only consider High and Critical servers
CVSS_THRESHOLD = 7.0  # Only consider CVEs with CVSS >= 7.0
