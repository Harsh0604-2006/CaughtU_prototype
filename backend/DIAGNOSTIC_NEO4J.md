# Diagnostic: Check Neo4j Node Properties

## Issue Identified

Your Neo4j instance is connected (we can see 93 nodes), but:

- ❌ Nodes don't have a `product` property (warning from Neo4j)
- ❌ No CVSS scores (showing as None)
- ❌ Node structure differs from expectations

## What We Know

From the output:

```
Total nodes: 93
Nodes: ForexSystem, MoneyMarket, ALMSystem, UEBAMonitor, InvestmentMgmt, ...
Properties: (unknown - let's discover)
```

## Solution: Run This Diagnostic Query

Execute this in Neo4j to see what properties exist:

```cypher
// Query 1: See all node labels and their counts
CALL db.labels() YIELD label
RETURN label, size(cypher("MATCH (n:" + label + ") RETURN n")) as count
```

```cypher
// Query 2: Sample node with ALL properties
MATCH (n)
RETURN labels(n) as labels,
       keys(n) as properties,
       n as sample_node
LIMIT 1
```

```cypher
// Query 3: List all property keys in database
CALL db.schema.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes
RETURN nodeType, propertyName, propertyTypes
```

```cypher
// Query 4: Specific node details (replace with actual node name if different)
MATCH (n {name: "ForexSystem"})
RETURN labels(n), apoc.map.fromPairs(collect([key, n[key]]) for key in keys(n))
```

## Next Steps

1. Run Query 1-4 in Neo4j Browser to understand current data structure
2. Check what properties your nodes actually have
3. Either:
   - **Option A:** Adapt nvd_sync.py/risk_calculator.py to use actual properties
   - **Option B:** Populate missing properties using Cypher update queries
   - **Option C:** Load the expected banking network schema

## Expected Structure (What We're Looking For)

```
Labels: [Server, Device, API, NetworkNode]
Properties:
  - name (string) ✓ Has
  - product (string) ✗ Missing
  - version (string) ?
  - criticality (string) ?
  - type (string) ?
  - cvss_score (float) ✗ Missing
  - exploit_available (string) ✗ Missing
```

## Quick Fix Option

If your nodes just need properties renamed:

```cypher
// Example: If nodes have 'application' instead of 'product'
MATCH (n)
WHERE n.application IS NOT NULL AND n.product IS NULL
SET n.product = n.application
```

---

**Once you identify the actual properties, we can update the scripts to use them.**
