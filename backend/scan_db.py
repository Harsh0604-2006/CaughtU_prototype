from neo4j_client import Neo4jClient

neo4j = Neo4jClient()

print("=" * 80)
print("FULL DATABASE SCAN")
print("=" * 80)

with neo4j.driver.session() as session:
    # Get all node labels
    result = session.run("CALL db.labels()")
    labels = [record[0] for record in result]
    print(f"\n[LABELS] {len(labels)} node labels found:")
    for label in labels:
        print(f"  - {label}")
    
    # Get node count by label
    print(f"\n[NODE COUNTS]")
    for label in labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as cnt")
        record = result.single()
        count = record['cnt'] if record else 0
        print(f"  {label}: {count} nodes")
    
    # Get all relationship types
    result = session.run("CALL db.relationshipTypes()")
    rel_types = [record[0] for record in result]
    print(f"\n[RELATIONSHIPS] {len(rel_types)} relationship types found:")
    for rel_type in rel_types:
        result = session.run(f"MATCH ()-[r:{rel_type}]-() RETURN count(r) as cnt")
        record = result.single()
        count = record['cnt'] if record else 0
        print(f"  {rel_type}: {count} relationships")
    
    # Get sample nodes from each label
    print(f"\n[SAMPLE NODES]")
    for label in labels:
        result = session.run(f"MATCH (n:{label}) RETURN n LIMIT 2")
        nodes = list(result)
        print(f"\n  {label}:")
        for node in nodes:
            n = node[0]
            props = dict(n)
            name = props.get('name', 'N/A')
            node_type = props.get('type', 'N/A')
            print(f"    - Name: {name}, Type: {node_type}, Props: {len(props)}")
    
    # Get all unique properties across all nodes
    print(f"\n[ALL PROPERTIES]")
    result = session.run("MATCH (n) UNWIND keys(n) AS key RETURN DISTINCT key ORDER BY key")
    properties = [record[0] for record in result]
    print(f"  {len(properties)} unique properties found:")
    for prop in properties:
        print(f"    - {prop}")
