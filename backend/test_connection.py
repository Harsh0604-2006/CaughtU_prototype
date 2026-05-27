#!/usr/bin/env python3
"""Test Neo4j connection and schema discovery"""

from neo4j_client import Neo4jClient

client = Neo4jClient()
print('✓ Neo4j connected' if client.check_connection() else '✗ Neo4j failed')
schema = client.discover_schema()
print(f'  Labels: {len(schema["node_labels"])}')
print(f'  Relationship Types: {len(schema["relationship_types"])}')

# Get total node count
with client.driver.session() as session:
    node_result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = node_result.single()["count"]
    print(f'  Total Nodes: {node_count}')
    
    # Get total relationship count
    rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = rel_result.single()["count"]
    print(f'  Total Relationships: {rel_count}')

client.close()
