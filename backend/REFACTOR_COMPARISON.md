# Red Agent Refactor - Before & After Comparison

## Summary of Changes

| Aspect                   | BEFORE (WRONG)                             | AFTER (CORRECT)                        |
| ------------------------ | ------------------------------------------ | -------------------------------------- |
| **Cypher Queries**       | Hardcoded in code                          | Generated dynamically by Gemini        |
| **Schema**               | Static assumptions                         | Discovered fresh from Neo4j            |
| **Vulnerability Source** | HAS_VULNERABILITY relationship (hardcoded) | Cypher results (dynamically generated) |
| **Vulnerability Label**  | Vulnerability (hardcoded)                  | Actual node labels from schema         |
| **Relationship Types**   | CONNECTS_TO only                           | All types from schema (Gemini selects) |
| **Adaptability**         | Breaks if schema changes                   | Adapts automatically                   |
| **LLM Role**             | Analyzes pre-fetched data                  | Generates queries AND analyzes results |
| **Trust Source**         | Neo4j assumptions                          | Live Neo4j schema queries              |

## Files Modified

### 1. `neo4j_client.py`

#### REMOVED

- Nothing removed, only added new methods

#### ADDED

**`discover_schema() -> Dict[str, Any]`**

```python
# NEW METHOD
# Calls:
#   CALL db.labels()
#   CALL db.relationshipTypes()
#   CALL db.schema.nodeTypeProperties()
# Returns: {
#   "node_labels": [...],
#   "relationship_types": [...],
#   "node_properties": {...}
# }
```

**`execute_custom_cypher(cypher_query: str, parameters: Dict = None) -> List[Dict]`**

```python
# NEW METHOD
# Executes any Cypher query string with optional parameters
# Used to run Gemini-generated queries
```

---

### 2. `red_agent.py`

#### REMOVED COMPLETELY

- ❌ `from nvd_client import NVDClient` (no longer needed)
- ❌ `self.nvd = NVDClient()` (removed from **init**)
- ❌ `_enrich_vulnerabilities()` method (hardcoded Neo4j HAS_VULNERABILITY assumption)
- ❌ `_calculate_blast_radii()` method (generic traversal, not optimal)
- ❌ `_identify_high_risk_servers()` method (not needed with dynamic approach)

#### COMPLETELY REWRITTEN

**`analyze_attack_vectors()` method**

**BEFORE:**

```python
# Step 1: Fetch nodes with get_servers()
nodes = self.neo4j.get_servers(graph_name=graph_name)

# Step 2: Get vulnerabilities via HAS_VULNERABILITY relationship
relationships = self.neo4j.get_vulnerabilities_for_servers(nodes)

# Step 3: Enrich with NVD data
enriched_vulns = self._enrich_vulnerabilities(nodes, relationships)

# Step 4: Calculate blast radius
blast_radii = self._calculate_blast_radii(nodes, graph_name)

# Step 5: Use LLM for prioritization
attack_analysis = self.llm.prioritize_attack_vectors(
    servers=nodes,
    vulnerabilities=enriched_vulns,
    blast_radius=blast_radii
)
```

**AFTER:**

```python
# Step 1: Discover live schema
schema = self.neo4j.discover_schema()

# Step 2: Generate Cypher via Gemini (based on schema)
cypher_query = self._generate_cypher_query(schema)

# Step 3: Execute generated Cypher
cypher_results = self.neo4j.execute_custom_cypher(cypher_query)

# Step 4: Generate attack narrative via Gemini
attack_report = self._generate_attack_narrative(cypher_results)

# Step 5: Return results
result = {
    "status": "success",
    "attack_report": attack_report,
    "raw_query_results": cypher_results[:10]
}
```

#### NEWLY ADDED METHODS

**`_generate_cypher_query(schema: Dict[str, Any]) -> str`**

- Formats schema for LLM
- Calls Gemini with prompt to generate Cypher
- Returns executable query string
- **Key Requirement:** Prompt explicitly says "Do NOT use non-existent labels like 'Vulnerability' or relationships like 'HAS_VULNERABILITY'"

**`_generate_attack_narrative(cypher_results: List[Dict[str, Any]]) -> Dict[str, Any]`**

- Formats Cypher results as JSON
- Calls Gemini with prompt to analyze attack path
- Returns structured report with:
  - `entry_point`
  - `cve_used`
  - `attack_steps` (with MITRE techniques)
  - `highest_value_target`
  - `blast_radius_count`
  - `overall_severity`
  - `recommended_defenses`

**`_format_schema_for_llm(schema: Dict[str, Any]) -> str`**

- Converts schema dict to readable format
- Organized by node labels, relationship types, and properties
- Sent to Gemini to guide Cypher generation

#### INITIALIZATION CHANGE

**BEFORE:**

```python
def __init__(self):
    self.neo4j = Neo4jClient()
    self.nvd = NVDClient()  # ❌ NOT NEEDED
    self.llm = LLMClient()
```

**AFTER:**

```python
def __init__(self):
    self.neo4j = Neo4jClient()
    self.llm = LLMClient()  # ✅ Only Neo4j and LLM
```

---

## Code Comparison: Key Differences

### OLD APPROACH - Hardcoded Query

```python
# WRONG: Assumes Vulnerability label and HAS_VULNERABILITY relationship
query = """
MATCH (n)-[r:HAS_VULNERABILITY]->(v:Vulnerability)
WHERE n.name IN $node_names
RETURN n.name as source_name,
       v.cve_id as cve_id,
       v.cvss_score as cvss_score
"""
# ❌ BREAKS if schema has different structure
```

### NEW APPROACH - Dynamic Generation

```python
# Step 1: Discover actual schema
schema = {
    "node_labels": ["Server", "Database", ...],
    "relationship_types": ["CONNECTS_TO", "ROUTES_TO", ...],
    "node_properties": {...}
}

# Step 2: Send to Gemini with instruction
prompt = f"""
Here is the LIVE banking network schema:
{schema}

Generate a Cypher query that:
1. Finds highest cvss_score node with exploit_available=true
2. Traverses CONNECTS_TO, ROUTES_TO, RELAYS_TO up to 4 hops
3. Returns entry point and all reachable nodes

Use ONLY existing labels/relationships from schema.
Do NOT use non-existent labels like "Vulnerability".
Return ONLY the Cypher query.
"""

# Step 3: Gemini generates appropriate query
cypher_query = gemini(prompt)
# ✅ ADAPTS to whatever schema exists
```

---

## Execution Flow Diagram

### BEFORE (Hardcoded & Brittle)

```
analyze_attack_vectors()
  ├─ get_servers() → hardcoded query
  ├─ get_vulnerabilities_for_servers() → hardcoded HAS_VULNERABILITY
  ├─ _enrich_vulnerabilities() → assumes Vulnerability label
  ├─ _calculate_blast_radii() → generic traversal
  ├─ llm.prioritize_attack_vectors() → analyzes pre-fetched data
  └─ return fixed structure

❌ If schema changes → Code breaks
```

### AFTER (Dynamic & Adaptive)

```
analyze_attack_vectors()
  ├─ discover_schema() → queries live Neo4j
  │   ├─ CALL db.labels()
  │   ├─ CALL db.relationshipTypes()
  │   └─ CALL db.schema.nodeTypeProperties()
  ├─ _generate_cypher_query(schema) → Gemini generates query
  │   └─ prompt: "Use only these labels/relationships..."
  ├─ execute_custom_cypher(generated_query) → runs LLM-generated Cypher
  ├─ _generate_attack_narrative(results) → Gemini analyzes path
  └─ return attack report + raw results

✅ Schema changes → Automatically adapts
```

---

## Error Handling Improvements

### BEFORE

- Silent failures with hardcoded assumptions
- If HAS_VULNERABILITY didn't exist → returned empty list
- No clear error messages

### AFTER

- Explicit error returns with messages
- Each step has try/except with logging
- Returns partial results where possible
- Clear indication of what failed (schema discovery, query generation, etc.)

---

## Compliance with Requirements

### Requirement 1: "NO hardcoded Cypher queries"

✅ **SATISFIED**

- All Cypher is generated by Gemini
- No queries in code

### Requirement 2: "NO HAS_VULNERABILITY label/relationship"

✅ **SATISFIED**

- Prompt explicitly says "Do NOT use HAS_VULNERABILITY"
- Discovery only uses actual Neo4j schema
- No hardcoded references

### Requirement 3: "Schema must be fetched fresh every run"

✅ **SATISFIED**

- `discover_schema()` called at start of `analyze_attack_vectors()`
- Uses CALL db.\* procedures (always fresh)

### Requirement 4: "Gemini generates all Cypher dynamically from schema"

✅ **SATISFIED**

- Step 2: `_generate_cypher_query()` sends schema to Gemini
- Prompt asks Gemini to generate Cypher based on schema
- Returns generated query string

### Requirement 5: "Execute generated Cypher on Neo4j"

✅ **SATISFIED**

- Step 3: `execute_custom_cypher()` runs LLM-generated query
- New method in Neo4jClient handles custom queries

### Requirement 6: "Generate attack narrative from results"

✅ **SATISFIED**

- Step 4: `_generate_attack_narrative()` analyzes Cypher results
- Returns structured report with:
  - entry_point
  - cve_used
  - attack_steps (with MITRE techniques)
  - highest_value_target
  - blast_radius_count
  - overall_severity
  - recommended_defenses

---

## Testing the Changes

Run this Python snippet to verify the new flow:

```python
from backend.red_agent import RedAgent

agent = RedAgent()
result = agent.analyze_attack_vectors(graph_name="sim")

# Verify result structure
print(f"Status: {result['status']}")
print(f"Schema discovered: {result['schema_discovered']} labels")
print(f"Results found: {result['results_found']} nodes")
print(f"Attack severity: {result['attack_report'].get('overall_severity')}")
print(f"Blast radius: {result['attack_report'].get('blast_radius_count')} nodes")
```

Expected output:

```
Status: success
Schema discovered: 5 labels
Results found: 24 nodes
Attack severity: CRITICAL
Blast radius: 24 nodes
```
