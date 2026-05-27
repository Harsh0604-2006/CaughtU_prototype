# Dynamic Risk Score Calculation Pipeline

## Overview

Risk scores are no longer hardcoded. They are calculated dynamically from **real signals**:

- **CVE Data** - CVSS score, exploit availability, attack vector
- **Graph Position** - How many nodes connect to it, how many critical nodes it can reach
- **Node Properties** - Type (Payment, Database), status, compromised state

---

## The Pipeline: Three Files, Three Steps

### Step 1: NVD Sync (`nvd_sync.py`) - Get Real CVE Data

```
┌─────────────────────────────────────┐
│ nvd_sync.py                         │
├─────────────────────────────────────┤
│ 1. Read product names from Neo4j    │
│ 2. Fetch CVEs for each product      │
│ 3. Write to nodes:                  │
│    - cvss_score (float)             │
│    - exploit_available (true/false) │
│    - attack_vector (Network/Local)  │
│    - cve_id (CVE-YYYY-XXXXX)        │
└─────────────────────────────────────┘
```

**Input:** Neo4j nodes with product names (OpenSSH, Apache, etc.)  
**Output:** Nodes enriched with CVE data

**Run:**

```bash
python nvd_sync.py prod          # Sync production graph
python nvd_sync.py sim           # Sync simulation graph
```

### Step 2: Risk Calculator (`risk_calculator.py`) - Calculate from Signals

```
┌────────────────────────────────────────┐
│ risk_calculator.py                     │
├────────────────────────────────────────┤
│ A. Calculate Blast Radius:             │
│    For each node, count critical      │
│    nodes it can reach (1..4 hops)     │
│    → Write blast_radius_count         │
│                                        │
│ B. Calculate Risk Score:               │
│    score = cve + exploit + vector +   │
│             blast + type + compromised│
│    → Write risk_score (0-100)         │
└────────────────────────────────────────┘
```

**Input:** Nodes with CVE data + graph topology  
**Output:** Nodes with blast_radius_count and risk_score

**Run:**

```bash
python risk_calculator.py prod   # Calculate scores
python risk_calculator.py sim
```

### Step 3: Red Agent - Use Dynamic Risk Scores

```
┌──────────────────────────────────────────┐
│ Red Agent (main.py, test_orchestrator)   │
├──────────────────────────────────────────┤
│ 1. Query schema from Neo4j               │
│ 2. Ask Gemini to generate Cypher that:   │
│    "Find node with highest risk_score"   │
│ 3. Traverse graph from that entry point  │
│ 4. Generate attack narrative             │
└──────────────────────────────────────────┘
```

**Input:** Neo4j with calculated risk_score  
**Output:** Attack path with highest-risk entry point

---

## Risk Score Formula

**Total Risk Score: 0-100 points**

### Component 1: CVE Severity (0-40 points)

```
cve_component = cvss_score * 4

cvss_score: 0.0  → 0 points
cvss_score: 5.0  → 20 points
cvss_score: 7.5  → 30 points
cvss_score: 10.0 → 40 points (max)
```

### Component 2: Exploit Availability (0-20 points)

```
IF exploit_available = "true"  → +20 points
ELSE                            → 0 points
```

### Component 3: Attack Vector (0-20 points)

```
IF attack_vector = "Network"  → +20 points
ELSE (Local/Physical)         → 0 points
```

### Component 4: Blast Radius (0-20 points)

```
Based on downstream_critical_nodes:

downstream_critical = 0     → 5 points
downstream_critical = 1-3   → 5 points
downstream_critical = 4-5   → 10 points
downstream_critical = 6-10  → 15 points
downstream_critical > 10    → 20 points (max)
```

### Bonuses: Node Type (0-5 points)

```
IF node.type IN ["Payment", "Database", "Finance", "Core"]
  → +5 points
```

### Bonuses: Compromised State (0-10 points)

```
IF node.compromised = true
  → +10 points (already breached)
```

### Final Calculation

```
raw_score = cve_component
          + exploit_component
          + vector_component
          + blast_component
          + type_boost
          + compromised_boost

risk_score = min(raw_score, 100)  # Cap at 100
```

---

## Database Schema Changes

### Nodes Before (Hardcoded Risk)

```
{name: "AUTH-03", product: "OpenSSH", risk_score: 85}  ❌ Hardcoded
```

### Nodes After (Dynamic Risk)

```
{
  name: "AUTH-03",
  product: "OpenSSH",
  cvss_score: 8.1,              ← From NVD (nvd_sync.py)
  exploit_available: "true",     ← From NVD (nvd_sync.py)
  attack_vector: "Network",      ← From NVD (nvd_sync.py)
  cve_id: "CVE-2024-6387",       ← From NVD (nvd_sync.py)
  cve_updated_at: <timestamp>,
  blast_radius_count: 14,        ← Calculated (risk_calculator.py)
  risk_score: 85,                ← Calculated (risk_calculator.py)
  risk_score_updated_at: <timestamp>,
  type: "Server",
  status: "Active",
  compromised: false
}  ✅ All dynamic
```

---

## Cypher Queries Used

### Query 1: Blast Radius Calculation

Used in `risk_calculator.py._calculate_blast_radius_scores()`

```cypher
MATCH (n)
WHERE n:Server OR n:NetworkNode OR n:Device OR n:API
OPTIONAL MATCH (n)-[:CONNECTS_TO|ROUTES_TO|RELAYS_TO*1..4]->(target)
WHERE target.type IN ["Database", "Payment", "Finance", "Core", "Critical"]
WITH n, count(DISTINCT target) as downstream_critical
SET n.blast_radius_count = downstream_critical
RETURN count(n) as updated_count
```

**What it does:**

- For each node (Server, Device, API)
- Find all nodes reachable via 1-4 hops through CONNECTS_TO, ROUTES_TO, RELAYS_TO
- Filter for important types (Database, Payment, Finance, Core)
- Count unique reachable nodes
- Store count as blast_radius_count

### Query 2: Risk Score Calculation

Used in `risk_calculator.py._calculate_risk_scores()`

```cypher
MATCH (n)
WHERE n:Server OR n:NetworkNode OR n:Device OR n:API
WITH n,
  // CVE component: 0-40 points
  (CASE WHEN n.cvss_score IS NOT NULL
        THEN toFloat(n.cvss_score) * 4
        ELSE 0
   END) as cve_component,

  // Exploit availability: 0-20 points
  (CASE WHEN n.exploit_available = "true"
        THEN 20
        ELSE 0
   END) as exploit_component,

  // Network attack vector: 0-20 points
  (CASE WHEN n.attack_vector = "Network" OR n.attack_vector = "NETWORK"
        THEN 20
        ELSE 0
   END) as vector_component,

  // Blast radius component: 0-20 points
  (CASE WHEN (n.blast_radius_count IS NULL OR n.blast_radius_count = 0)
        THEN 5
        WHEN n.blast_radius_count > 10
        THEN 20
        WHEN n.blast_radius_count > 5
        THEN 15
        WHEN n.blast_radius_count > 3
        THEN 10
        ELSE 5
   END) as blast_component

// Additional boost for already compromised nodes
WITH n, cve_component, exploit_component, vector_component, blast_component,
     (CASE WHEN n.compromised = true
           THEN 10
           ELSE 0
      END) as compromised_boost

// Additional boost for high-value node types
WITH n, cve_component, exploit_component, vector_component, blast_component, compromised_boost,
     (CASE WHEN n.type IN ["Payment", "Database", "Finance", "Core"]
           THEN 5
           ELSE 0
      END) as type_boost

// Calculate final score (capped at 100)
WITH n,
     cve_component + exploit_component + vector_component + blast_component + compromised_boost + type_boost as raw_score

SET n.risk_score = CASE WHEN raw_score > 100 THEN 100 ELSE raw_score END,
    n.risk_score_updated_at = datetime()

RETURN count(n) as updated_count
```

**What it does:**

- Calculate each component of the risk formula
- Apply bonuses for node type and compromised state
- Cap final score at 100
- Write risk_score and timestamp to node

---

## Running the Pipeline

### Full Automated Run

```bash
# Run all steps in sequence
python nvd_sync.py sim                    # Step 1: Get CVE data
python risk_calculator.py sim             # Step 2: Calculate scores
python main.py                            # Step 3: Start server with Red Agent
```

### Individual Component Test

```bash
# Test just NVD sync
from nvd_sync import run_nvd_sync
result = run_nvd_sync("sim")
print(f"Nodes enriched: {result['nodes_enriched']}")

# Test just risk calculation
from risk_calculator import run_risk_calculation
result = run_risk_calculation("sim")
print(f"Risk scores updated: {result['risk_score_nodes_updated']}")

# Test Red Agent with calculated scores
from red_agent import RedAgent
agent = RedAgent()
result = agent.analyze_attack_vectors("sim")
print(f"Entry point: {result['attack_report']['entry_point']}")
```

---

## What Changed from Before

### BEFORE (Hardcoded Risk)

```python
# Manually typed risk_scores into Neo4j
nodes = [
    {"name": "AUTH-03", "risk_score": 85},      ❌ Hardcoded
    {"name": "PAYMENT-01", "risk_score": 92},   ❌ Hardcoded
    {"name": "FILE-01", "risk_score": 45}       ❌ Hardcoded
]

# Red Agent queries highest risk node
# Threat: If risk_scores are wrong, attack path is wrong
```

### AFTER (Dynamic Risk)

```python
# NVD sync writes real CVE data
nodes = [
    {
        "name": "AUTH-03",
        "cvss_score": 8.1,              ✅ Real CVE data
        "exploit_available": "true",    ✅ Real CVE data
        "attack_vector": "Network"      ✅ Real CVE data
    }
]

# Risk calculator computes from formula
# risk_score = (8.1 * 4) + 20 + 20 + 15 = 87.4 → 87

# Red Agent queries highest risk node
# Fact: Risk score accurately reflects vulnerability + graph position
```

---

## Benefits

✅ **No Hardcoding**

- Risk scores come from real data (NVD CVEs + Neo4j topology)
- No manual entry = no human error

✅ **Reproducible**

- Same graph → Same risk scores every time
- Formula is transparent and auditable

✅ **Adaptive**

- Graph changes? Scores automatically recalculate
- New CVEs discovered? Scores update next run

✅ **Defensible**

- Scores are justified (CVE data + graph position)
- Can explain why a node has high risk

✅ **Extensible**

- Add new signals to formula (CVSS temporal score, exploit difficulty, etc.)
- Adjust weights to match organizational risk tolerance

---

## Monitoring & Debugging

### Check CVE Data Written

```cypher
MATCH (n)
WHERE n.cvss_score IS NOT NULL
RETURN n.name, n.cvss_score, n.exploit_available, n.cve_id
ORDER BY n.cvss_score DESC
LIMIT 10
```

### Check Blast Radius Calculation

```cypher
MATCH (n)
WHERE n.blast_radius_count IS NOT NULL
RETURN n.name, n.blast_radius_count, n.type
ORDER BY n.blast_radius_count DESC
LIMIT 10
```

### Check Risk Scores Distribution

```cypher
MATCH (n)
WHERE n.risk_score IS NOT NULL
RETURN
  count(CASE WHEN n.risk_score >= 80 THEN 1 END) as critical,
  count(CASE WHEN n.risk_score >= 60 AND n.risk_score < 80 THEN 1 END) as high,
  count(CASE WHEN n.risk_score >= 40 AND n.risk_score < 60 THEN 1 END) as medium,
  count(CASE WHEN n.risk_score < 40 THEN 1 END) as low,
  min(n.risk_score) as min_risk,
  max(n.risk_score) as max_risk
```

### Check Highest Risk Nodes

```python
from risk_calculator import RiskCalculator

calc = RiskCalculator()
high_risk = calc.get_highest_risk_nodes(limit=10)
for node in high_risk:
    print(f"{node['name']}: {node['risk_score']} "
          f"(CVSS: {node['cvss_score']}, Blast: {node['blast_radius']})")
```

---

## Error Handling

### If NVD sync fails:

- Check Neo4j connection
- Check that nodes have a "product" property
- Check GEMINI_API_KEY if using live NVD API

### If risk calculation fails:

- Check that NVD sync was run first (cvss_score must exist)
- Check that graph has proper node labels (Server, Device, API)
- Check that relationships use correct types (CONNECTS_TO, ROUTES_TO, RELAYS_TO)

### If Red Agent fails to find entry point:

- Check that risk_calculator was run
- Verify nodes have risk_score property with Cypher query above
- Ensure at least one node has cvss_score + exploit_available = true

---

## Integration with Red Agent

**Red Agent Flow with Dynamic Risk:**

```
Red Agent.analyze_attack_vectors()
├─ discover_schema()
├─ _generate_cypher_query(schema)
│  └─ Gemini generates:
│     "Find node with highest risk_score"
│     "where exploit_available = true"
│     "then traverse CONNECTS_TO, ROUTES_TO for 4 hops"
├─ execute_custom_cypher()
│  └─ Gets entry_point = AUTH-03 (risk: 87)
│  └─ Gets reachable nodes with risk_scores
├─ _generate_attack_narrative()
│  └─ Analyzes attack path with risks
└─ return attack_report
```

Entry point is selected because:

1. ✅ Has highest risk_score
2. ✅ Has real CVE data (cvss_score 8.1)
3. ✅ Has exploit available
4. ✅ Risk score reflects both vulnerability AND graph position
5. ✅ Not hardcoded - purely data-driven

---

## File Locations

```
backend/
├── nvd_sync.py           ← Step 1: Fetch CVE data
├── risk_calculator.py    ← Step 2: Calculate risk scores
├── red_agent.py          ← Step 3: Use risk scores (already updated)
├── neo4j_client.py       ← Shared DB client
├── nvd_client.py         ← Shared NVD client
└── main.py               ← FastAPI server (orchestrates all)
```

---

## Summary

| Aspect                | Before                      | After                            |
| --------------------- | --------------------------- | -------------------------------- |
| Risk scores           | Hardcoded manually          | Calculated from formula          |
| CVE data              | Missing/stale               | Fresh from NVD                   |
| Graph position        | Ignored                     | Used in blast_radius calculation |
| Entry point selection | Random/arbitrary            | Highest risk_score (justified)   |
| Maintainability       | Breaks with graph changes   | Auto-adapts                      |
| Auditability          | "Why is AUTH-03 high risk?" | "CVSS 8.1 + 14 downstream nodes" |

**Result:** Risk-driven attack analysis, not guesswork. ✅
