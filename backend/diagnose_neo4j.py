#!/usr/bin/env python3
"""
Diagnostic Script: Check Neo4j Instance & Data Structure
Helps identify what properties exist and what's missing
"""

from neo4j import GraphDatabase
import json
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def diagnose_database():
    """Run diagnostic queries to understand database structure"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("=" * 80)
            print("NEO4J DATABASE DIAGNOSTIC")
            print("=" * 80)
            
            # Test 1: Connection
            print("\n1. CONNECTION TEST")
            result = session.run("RETURN 1 as connected")
            print("   ✓ Connected to Neo4j AuraDB")
            
            # Test 2: Node labels
            print("\n2. NODE LABELS IN DATABASE")
            result = session.run("CALL db.labels() YIELD label RETURN label")
            labels = [record["label"] for record in result]
            print(f"   Found {len(labels)} labels:")
            for label in labels:
                print(f"      - {label}")
            
            # Test 3: Node counts by label
            print("\n3. NODE COUNTS BY LABEL")
            result = session.run("""
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {})
                YIELD value
                RETURN label, value.count as count
                ORDER BY count DESC
            """)
            for record in result:
                print(f"   {record['label']:20} : {record['count']:5} nodes")
            
            # Test 4: Sample node and properties
            print("\n4. SAMPLE NODE & PROPERTIES")
            result = session.run("""
                MATCH (n)
                RETURN labels(n) as labels,
                       keys(n) as properties,
                       n as node
                LIMIT 1
            """)
            record = result.single()
            if record:
                print(f"   Labels: {record['labels']}")
                print(f"   Properties found: {record['properties']}")
                print(f"\n   Sample node data:")
                node = record['node']
                for key in record['properties']:
                    print(f"      - {key}: {node[key]}")
            
            # Test 5: Property coverage
            print("\n5. CRITICAL PROPERTIES - COVERAGE REPORT")
            critical_props = ['product', 'name', 'type', 'criticality', 'cvss_score', 'exploit_available', 'attack_vector']
            for prop in critical_props:
                result = session.run(f"""
                    MATCH (n)
                    WHERE n.{prop} IS NOT NULL
                    RETURN count(n) as count
                """)
                count = result.single()["count"]
                total_result = session.run("MATCH (n) RETURN count(n) as total")
                total = total_result.single()["total"]
                pct = (count / total * 100) if total > 0 else 0
                status = "✓" if count > 0 else "✗"
                print(f"   {status} {prop:20} : {count:5}/{total:5} nodes ({pct:5.1f}%)")
            
            # Test 6: All properties in database
            print("\n6. ALL PROPERTIES AVAILABLE")
            result = session.run("""
                MATCH (n)
                UNWIND keys(n) as key
                RETURN DISTINCT key
                ORDER BY key
            """)
            all_props = [record['key'] for record in result]
            print(f"   Total unique properties: {len(all_props)}")
            for prop in all_props:
                print(f"      - {prop}")
            
            # Test 7: Relationship types
            print("\n7. RELATIONSHIP TYPES")
            result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
            rel_types = [record['relationshipType'] for record in result]
            if rel_types:
                for rel_type in rel_types:
                    print(f"      - {rel_type}")
            else:
                print("      (None)")
            
            # Test 8: Total stats
            print("\n8. OVERALL STATISTICS")
            result = session.run("""
                MATCH (n)
                MATCH ()-[r]->()
                RETURN count(DISTINCT n) as nodes, count(r) as relationships
            """)
            record = result.single()
            print(f"   Total nodes: {record['nodes']}")
            print(f"   Total relationships: {record['relationships']}")
            
            # Test 9: Sample data query
            print("\n9. SAMPLE DATA (first 5 nodes)")
            result = session.run("""
                MATCH (n)
                RETURN n.name as name, labels(n) as labels
                LIMIT 5
            """)
            for record in result:
                print(f"   - {record['name']} ({', '.join(record['labels'])})")
            
    finally:
        driver.close()
    
    print("\n" + "=" * 80)
    print("END DIAGNOSTIC")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_database()
