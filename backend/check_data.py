#!/usr/bin/env python3
"""Check what data is actually in the database"""

from neo4j_client import Neo4jClient

client = Neo4jClient()

# Get top 10 nodes by risk score with all their properties
result = client.execute_custom_cypher('''
MATCH (n)
WHERE n.risk_score IS NOT NULL
RETURN 
  n.name as name,
  n.risk_score as risk_score,
  n.incoming_relationship_count as incoming,
  n.blast_radius_count as blast_radius,
  n.cvss_score as cvss_score,
  n.exploit_available as exploit_available,
  n.attack_vector as attack_vector,
  labels(n) as labels
ORDER BY n.risk_score DESC
LIMIT 10
''')

print("\n=== TOP 10 NODES IN DATABASE ===\n")
for i, record in enumerate(result, 1):
    print(f"{i}. {record['name']}")
    print(f"   Risk Score: {record['risk_score']}")
    print(f"   Incoming: {record['incoming']}")
    print(f"   Blast Radius: {record['blast_radius']}")
    print(f"   CVSS: {record['cvss_score']}")
    print(f"   Exploit Available: {record['exploit_available']}")
    print(f"   Attack Vector: {record['attack_vector']}")
    print(f"   Labels: {record['labels']}")
    print()

client.close()
