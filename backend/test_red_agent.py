#!/usr/bin/env python3
"""Test Red Agent directly to see what error occurs"""

import json
from red_agent import RedAgent

print("Testing Red Agent...")
try:
    agent = RedAgent()
    print("✓ Red Agent initialized\n")
    
    result = agent.analyze_attack_vectors(graph_name="prod")
    
    print(f"Status: {result.get('status')}")
    print(f"Graph: {result.get('graph')}")
    print(f"Schema Discovered: {result.get('schema_discovered')}")
    print(f"Cypher Executed: {result.get('cypher_executed')}")
    print(f"Results Found: {result.get('results_found')}")
    print(f"\nAttack Report:")
    print(result.get('attack_report', {}))
    print(f"\nRaw Results Count: {len(result.get('raw_query_results', []))}")
    if result.get('raw_query_results'):
        print(f"First result: {result['raw_query_results'][0]}")
        
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
