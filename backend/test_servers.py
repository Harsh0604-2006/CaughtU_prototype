#!/usr/bin/env python3
"""Test the get_servers endpoint"""

from neo4j_client import Neo4jClient

print("Testing get_servers endpoint...")
try:
    client = Neo4jClient()
    
    # Test with prod
    servers = client.get_servers(graph_name="prod")
    print(f"✓ Servers retrieved: {len(servers)}")
    
    if servers:
        print(f"First server: {servers[0]}")
    
    client.close()
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
