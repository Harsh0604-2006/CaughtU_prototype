# Gemini Prompts Reference

This document contains the exact prompts sent to Gemini API in the refactored Red Agent.

## Prompt 1: Cypher Generation

**Location:** `red_agent.py` → `_generate_cypher_query()` method

**Purpose:** Generate a dynamic Cypher query based on live Neo4j schema

**Sent To:** `self.llm.client.generate_content(prompt, generation_config={...})`

**Configuration:**

- Model: gemini-2.5-flash
- Max tokens: 1000
- Temperature: 0.3 (deterministic)

**Exact Prompt Text:**

```
You are a Neo4j Cypher expert analyzing a banking network graph.
Here is the live banking network graph schema:

[SCHEMA - formatted as NODE LABELS, RELATIONSHIP TYPES, NODE PROPERTIES]

Generate a SINGLE Cypher query that:
1. Finds the highest cvss_score node where exploit_available is true (entry point)
2. From that node, traverses CONNECTS_TO, ROUTES_TO, and RELAYS_TO relationships up to 4 hops
3. Finds all reachable nodes and returns:
   - entry_node name and cvss_score and cve_id
   - Each reachable node name, risk_score, and path relationship type

Requirements:
- Use only existing node labels and relationship types from the schema
- Do NOT use non-existent labels like "Vulnerability" or relationships like "HAS_VULNERABILITY"
- Return only the Cypher query, no explanation
- The query must be executable as-is
- Use DISTINCT to avoid duplicates
- Order by risk_score descending
- LIMIT 100 results

Return ONLY the Cypher code, nothing else. Start with MATCH, end with appropriate RETURN clause.
```

**Schema Format Example:**

```
NODE LABELS:
  - Server
  - Device
  - Database
  - Network
  - Router

RELATIONSHIP TYPES:
  - CONNECTS_TO
  - ROUTES_TO
  - RELAYS_TO
  - DEPENDS_ON
  - MANAGES

NODE PROPERTIES PER LABEL:
  Server:
    - name (STRING)
    - product (STRING)
    - version (STRING)
    - ip (STRING)
    - os (STRING)
    - type (STRING)
    - criticality (STRING)
    - zone (STRING)
    - cvss_score (FLOAT)
    - exploit_available (BOOLEAN)
    - cve_id (STRING)
    - risk_score (FLOAT)
  Device:
    - name (STRING)
    - type (STRING)
    - criticality (STRING)
    - risk_score (FLOAT)
    - ...
```

**Expected Output:**

A Cypher query like:

```cypher
MATCH (entry {cvss_score: max(cvss_score), exploit_available: true})
MATCH (entry)-[r1:CONNECTS_TO|ROUTES_TO|RELAYS_TO*1..4]->(reachable)
RETURN DISTINCT
  entry.name as entry_point,
  entry.cvss_score as entry_cvss,
  entry.cve_id as entry_cve,
  reachable.name as reachable_node,
  reachable.risk_score as node_risk,
  type(r1) as path_relationship
ORDER BY reachable.risk_score DESC
LIMIT 100
```

**Key Constraints in Prompt:**

- ✅ "Use only existing node labels and relationship types from the schema"
- ✅ "Do NOT use non-existent labels like 'Vulnerability'"
- ✅ "Do NOT use relationships like 'HAS_VULNERABILITY'"
- ✅ "Return ONLY the Cypher query, no explanation"
- ✅ "The query must be executable as-is"

---

## Prompt 2: Attack Narrative Generation

**Location:** `red_agent.py` → `_generate_attack_narrative()` method

**Purpose:** Analyze Cypher query results and generate structured attack report

**Sent To:** `self.llm.client.generate_content(prompt, generation_config={...})`

**Configuration:**

- Model: gemini-2.5-flash
- Max tokens: 2000
- Temperature: 0.5 (balanced)

**Exact Prompt Text:**

```
You are a Red Team analyst for a banking network.
Here are the results of a graph traversal showing an attack path through a bank network:

ATTACK PATH RESULTS:
[CYPHER RESULTS - first 50 results as JSON]

Analyze this attack path and generate a structured red team attack report.

The report MUST include:
- entry_point: Name of the compromised node (highest cvss_score)
- cve_used: The CVE identifier of the initial exploit
- attack_steps: A list where each step has:
  - step: step number
  - action: what the attacker does
  - mitre_technique: MITRE ATT&CK technique (e.g., T1021.006)
  - target_node: which node is compromised in this step
  - result: outcome of this step
- highest_value_target: The most critical node reachable (typically banking infrastructure)
- blast_radius_count: Total number of nodes compromised/reachable
- overall_severity: "CRITICAL", "HIGH", "MEDIUM", or "LOW"
- recommended_defenses: List of immediate defensive actions

Return as valid JSON only, no explanations. Format:
{
  "entry_point": "...",
  "cve_used": "...",
  "attack_steps": [
    {"step": 1, "action": "...", "mitre_technique": "...", "target_node": "...", "result": "..."}
  ],
  "highest_value_target": "...",
  "blast_radius_count": N,
  "overall_severity": "...",
  "recommended_defenses": [...]
}
```

**Cypher Results Format Example:**

```json
[
  {
    "entry_point": "AUTH-03",
    "entry_cvss": 9.2,
    "entry_cve": "CVE-2021-12345",
    "reachable_node": "FILE-SERVER-01",
    "node_risk": 7.5,
    "path_relationship": "CONNECTS_TO"
  },
  {
    "entry_point": "AUTH-03",
    "entry_cvss": 9.2,
    "entry_cve": "CVE-2021-12345",
    "reachable_node": "PAYMENT-PROCESSOR",
    "node_risk": 8.9,
    "path_relationship": "ROUTES_TO"
  },
  ...
]
```

**Expected Output:**

```json
{
  "entry_point": "AUTH-03",
  "cve_used": "CVE-2021-12345",
  "attack_steps": [
    {
      "step": 1,
      "action": "Exploit SSH vulnerability in AUTH-03 authentication server",
      "mitre_technique": "T1021.006 (OpenSSH SSH Remote Access)",
      "target_node": "AUTH-03",
      "result": "Remote code execution and system access achieved"
    },
    {
      "step": 2,
      "action": "Lateral movement to FILE-SERVER-01 via network connection",
      "mitre_technique": "T1021.002 (Windows Remote Service SSH)",
      "target_node": "FILE-SERVER-01",
      "result": "Access to sensitive banking documents acquired"
    },
    {
      "step": 3,
      "action": "Pivot to PAYMENT-PROCESSOR through routed connection",
      "mitre_technique": "T1021.001 (Windows Remote Service RDP)",
      "target_node": "PAYMENT-PROCESSOR",
      "result": "Control of payment processing system achieved"
    }
  ],
  "highest_value_target": "PAYMENT-PROCESSOR",
  "blast_radius_count": 24,
  "overall_severity": "CRITICAL",
  "recommended_defenses": [
    "Immediately patch AUTH-03 with latest security updates",
    "Isolate PAYMENT-PROCESSOR from network temporarily",
    "Block SSH connections from external sources",
    "Implement network segmentation between AUTH and PAYMENT tiers",
    "Conduct forensic analysis of all systems in blast radius"
  ]
}
```

---

## Prompt Template Variables

Both prompts use template variables:

### Prompt 1: Cypher Generation

```python
schema_text = self._format_schema_for_llm(schema)
prompt = f"""You are a Neo4j Cypher expert...
Here is the live banking network graph schema:

{schema_text}  # ← VARIABLE: Formatted Neo4j schema

Generate a SINGLE Cypher query that:
..."""
```

### Prompt 2: Attack Narrative

```python
results_text = json.dumps(cypher_results[:50], indent=2)
prompt = f"""You are a Red Team analyst...
Here are the results of a graph traversal:

ATTACK PATH RESULTS:
{results_text}  # ← VARIABLE: Cypher query results

Analyze this attack path and generate a structured report...
..."""
```

---

## Configuration & Temperature Settings

**Temperature Explanation:**

| Prompt            | Temperature | Reason                                                         |
| ----------------- | ----------- | -------------------------------------------------------------- |
| Cypher Generation | 0.3         | Low - needs consistent, correct syntax                         |
| Attack Narrative  | 0.5         | Medium - allows creativity for narrative while staying focused |

**Max Token Limits:**

| Prompt            | Max Tokens | Reason                                          |
| ----------------- | ---------- | ----------------------------------------------- |
| Cypher Generation | 1000       | Cypher queries are typically short              |
| Attack Narrative  | 2000       | Attack reports need detailed steps and defenses |

---

## How Prompts Ensure Compliance

### Requirement: "NO hardcoded Cypher queries"

**Enforced by Prompt 1:**

> "Use only existing node labels and relationship types from the schema"
> "Do NOT use non-existent labels like 'Vulnerability'"

The schema is discovered fresh and passed to Gemini, so Gemini adapts to whatever exists.

### Requirement: "NO HAS_VULNERABILITY relationship"

**Enforced by Prompt 1:**

> "Do NOT use relationships like 'HAS_VULNERABILITY'"

Explicit instruction prevents Gemini from using hardcoded relationship names.

### Requirement: "Gemini generates Cypher dynamically"

**Enforced by Prompt 1:**

> "Generate a SINGLE Cypher query that: 1. Finds the highest cvss_score node..."
> "Return ONLY the Cypher code, nothing else"

Gemini is explicitly asked to generate the query, not retrieve a pre-written one.

### Requirement: "Execute generated Cypher"

**Enforced by Code:**

```python
cypher_query = self._generate_cypher_query(schema)  # Get from Gemini
cypher_results = self.neo4j.execute_custom_cypher(cypher_query)  # Execute
```

### Requirement: "Generate attack narrative"

**Enforced by Prompt 2:**

> "Analyze this attack path and generate a structured red team attack report"
> "The report MUST include: entry_point, cve_used, attack_steps, ..."

Prompt explicitly requires structured narrative with all required fields.

---

## Debugging Prompts

If you need to test or modify prompts, here's how to do it:

### Test Prompt 1 (Cypher Generation)

```python
from red_agent import RedAgent
from neo4j_client import Neo4jClient

neo4j = Neo4jClient()
schema = neo4j.discover_schema()
schema_text = RedAgent()._format_schema_for_llm(schema)
print(schema_text)  # See what's sent to Gemini
```

### Test Prompt 2 (Attack Narrative)

```python
import json
# Get sample results from your database
cypher_results = [...]  # Your results
results_text = json.dumps(cypher_results[:50], indent=2)
print(results_text)  # See what's sent to Gemini
```

---

## Future Customization

To modify what Gemini generates, edit the prompt strings in:

- `_generate_cypher_query()` for Cypher logic changes
- `_generate_attack_narrative()` for attack report structure changes

Always ensure:

1. ✅ Prompts are explicit about constraints
2. ✅ Temperature reflects use case (0.3 for code, 0.5-0.7 for narrative)
3. ✅ Response format is specified (Cypher only, JSON only, etc.)
4. ✅ Max tokens are appropriate for expected response length
