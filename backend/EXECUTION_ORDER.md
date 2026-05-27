# Execution Order & Dependencies

## The Correct Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│ YOU: Run these 3 commands in order                              │
└─────────────────────────────────────────────────────────────────┘

1. python nvd_sync.py sim
   ↓ (writes cvss_score, exploit_available, attack_vector)
2. python risk_calculator.py sim
   ↓ (writes blast_radius_count, risk_score)
3. python main.py
   ↓ (starts server, Red Agent queries risk_score)
4. GET http://localhost:8000/analyze-attack-vectors?graph=sim
   ↓ (returns attack path with dynamic risk entry point)
```

---

## Why This Order Matters

### ❌ WRONG: Run risk_calculator BEFORE nvd_sync

```bash
python risk_calculator.py sim       # WRONG!
python nvd_sync.py sim
```

**Problem:** risk_calculator needs `cvss_score` to calculate, but nvd_sync hasn't run yet.
**Result:** All nodes have risk_score = 5 (minimum, no CVE data)

### ❌ WRONG: Run Red Agent BEFORE risk_calculator

```bash
python nvd_sync.py sim
python main.py                      # WRONG!
python risk_calculator.py sim
```

**Problem:** Red Agent queries `risk_score`, but it hasn't been calculated yet.
**Result:** Red Agent finds nodes with risk_score = 0 or NULL

### ✅ CORRECT: Run in order

```bash
python nvd_sync.py sim              # Writes CVE data
python risk_calculator.py sim       # Calculates risk scores
python main.py                      # Queries risk scores
```

**Result:** Everything works, entry point is highest-risk node ✅

---

## Dependency Graph

```
nvd_client.py ─────────┐
neo4j_client.py ─────┬─┴──→ nvd_sync.py
config.py ───────────┘      (Step 1)
                              ↓
                           ✅ Nodes have:
                           - cvss_score
                           - exploit_available
                           - attack_vector
                           - cve_id
                              ↓
neo4j_client.py ─────────→ risk_calculator.py
config.py ───────────┘      (Step 2)
                              ↓
                           ✅ Nodes have:
                           - blast_radius_count
                           - risk_score
                              ↓
llm_client.py ────────┐
neo4j_client.py ─────┬─→ red_agent.py
config.py ───────────┘   (Step 3, in main.py)
                            ↓
                         ✅ Uses:
                         - risk_score for entry point
                         - Cypher to find highest
                         - Attack narrative
```

---

## Files in Execution Order

### BEFORE Pipeline Runs

```
Files already in backend/:
├── config.py ........................ Configuration (no changes needed)
├── neo4j_client.py .................. DB client (new methods added)
├── llm_client.py .................... LLM client (no changes needed)
├── nvd_client.py .................... NVD client (no changes needed)
├── red_agent.py ..................... Red Agent (REFACTORED - schema driven)
└── main.py .......................... FastAPI server (runs everything)
```

### NEW Files Added

```
├── nvd_sync.py ...................... Step 1: Fetch CVE data ✅ NEW
├── risk_calculator.py ............... Step 2: Calculate scores ✅ NEW
└── Documentation:
    ├── DYNAMIC_RISK_SCORING.md ....... Complete guide ✅ NEW
    ├── QUICK_START_DYNAMIC_RISK.md ... Quick start ✅ NEW
    └── IMPLEMENTATION_COMPLETE.md .... Summary ✅ NEW
```

---

## Detailed Step-by-Step

### Step 1: NVD Sync

**File:** `nvd_sync.py`  
**Imports:** `neo4j_client`, `nvd_client`, `config`  
**Depends on:** Neo4j connection, nvd_client working

**Execution:**

```bash
python nvd_sync.py sim
```

**What happens:**

1. Initialize Neo4jClient() → connect to database
2. Query: Get all unique node.product values
3. For each product:
   - Call nvd_client.get_cves_for_product(product)
   - Get list of CVEs with cvss_score, exploit_available, attack_vector
4. For each product, update all nodes with that product:
   ```cypher
   SET n.cvss_score = X
   SET n.exploit_available = "true/false"
   SET n.attack_vector = "Network"
   SET n.cve_id = "CVE-2024-XXXX"
   SET n.cve_updated_at = now()
   ```

**Result:** Nodes now have real CVE data ✅

---

### Step 2: Risk Calculator

**File:** `risk_calculator.py`  
**Imports:** `neo4j_client`, `config`  
**Depends on:** Step 1 complete (nvd_sync.py ran)  
**Prerequisite:** Nodes must have `cvss_score` property

**Execution:**

```bash
python risk_calculator.py sim
```

**What happens:**

**Phase A - Blast Radius:**

1. Query all nodes (Server, Device, API)
2. For each node, traverse graph:
   - Go 1-4 hops through CONNECTS_TO, ROUTES_TO, RELAYS_TO
   - Count nodes with type IN ["Database", "Payment", "Finance", "Core"]
   - Store count as `blast_radius_count`

**Phase B - Risk Score:**

1. Query all nodes again
2. For each node, calculate:

   ```
   cve_part = cvss_score * 4          (0-40)
   exploit_part = 20 if exploit else 0 (0-20)
   vector_part = 20 if Network else 0  (0-20)
   blast_part = map(blast_count)       (0-20)
   type_part = 5 if critical type      (0-5)
   compromised_part = 10 if breached   (0-10)

   risk_score = min(sum_all, 100)
   ```

3. Store as `risk_score` and `risk_score_updated_at`

**Result:** Nodes now have calculated risk_score ✅

---

### Step 3: Red Agent (in main.py)

**File:** `red_agent.py` (called from `main.py`)  
**Imports:** `neo4j_client`, `llm_client`, `config`  
**Depends on:** Step 2 complete (risk_calculator.py ran)  
**Prerequisite:** Nodes must have `risk_score` property

**Execution:**

```bash
python main.py
# Server starts listening on port 8000
# GET http://localhost:8000/analyze-attack-vectors?graph=sim
```

**What happens:**

1. Red Agent discovers schema from Neo4j
2. Sends schema to Gemini:
   ```
   "Generate Cypher to find highest risk_score node"
   ```
3. Gemini generates (example):
   ```cypher
   MATCH (entry)
   WHERE entry.risk_score = max(risk_score)
     AND entry.exploit_available = "true"
   MATCH (entry)-[:CONNECTS_TO|...*1..4]->(reachable)
   RETURN entry, reachable
   ```
4. Executes Cypher against Neo4j
5. Finds AUTH-03 (risk_score: 87)
6. Sends results to Gemini for narrative:
   ```
   "Analyze this attack path and generate report"
   ```
7. Returns JSON with attack narrative

**Result:** Attack path with AUTH-03 as entry point ✅

---

## Checking Progress Between Steps

### After Step 1 (NVD Sync)

```python
# Check if CVE data was written
from neo4j_client import Neo4jClient

neo4j = Neo4jClient()
with neo4j.driver.session() as session:
    result = session.run("MATCH (n) WHERE n.cvss_score IS NOT NULL RETURN count(n)")
    print(f"Nodes with CVE data: {result.single()[0]}")
    # Should be > 0
```

### After Step 2 (Risk Calculator)

```python
# Check if risk scores were calculated
from neo4j_client import Neo4jClient

neo4j = Neo4jClient()
with neo4j.driver.session() as session:
    result = session.run("""
        MATCH (n) WHERE n.risk_score IS NOT NULL
        RETURN n.name, n.risk_score
        ORDER BY n.risk_score DESC
        LIMIT 5
    """)
    for record in result:
        print(f"{record['name']}: {record['risk_score']}")
    # Should show nodes with scores 0-100
```

### After Step 3 (Red Agent Ready)

```bash
# Test Red Agent API
curl http://localhost:8000/analyze-attack-vectors?graph=sim | python -m json.tool

# Should return:
{
  "status": "success",
  "attack_report": {
    "entry_point": "AUTH-03",        ← Highest risk_score node
    "overall_severity": "CRITICAL",
    "blast_radius_count": 14,
    ...
  }
}
```

---

## What Goes Wrong If You Skip Steps

### Scenario: Skip nvd_sync, run risk_calculator directly

```bash
python risk_calculator.py sim  # ❌ WRONG
```

**Problem:**

```cypher
-- risk_calculator tries to calculate:
cve_component = cvss_score * 4
-- But cvss_score is NULL because nvd_sync didn't run

-- Result:
cve_component = NULL
-- Which becomes 0
```

**Effect:** All nodes get low risk_score (5-15), no realistic entry points

---

### Scenario: Run main.py before risk_calculator

```bash
python main.py  # ❌ WRONG
```

**Problem:**

```
Red Agent queries: "Find node with highest risk_score"
-- But risk_score hasn't been calculated
-- Returns nodes with risk_score = NULL

Red Agent can't proceed
```

**Effect:** API fails or returns meaningless results

---

## Complete Timeline

```
Time T=0:00 - User decision
  "I want dynamic risk scores"

Time T=0:05 - NVD Sync
  $ python nvd_sync.py sim
  ✓ Connected to Neo4j
  ✓ Found 5 products
  ✓ Fetched 12 CVEs
  ✓ Updated 14 nodes
  [nodes now have: cvss_score, exploit_available, attack_vector]

Time T=0:10 - Risk Calculator Phase 1
  $ python risk_calculator.py sim
  ✓ Connected to Neo4j
  ✓ Calculated blast radius for 24 nodes
  [nodes now have: blast_radius_count]

Time T=0:15 - Risk Calculator Phase 2
  ✓ Calculated risk scores for 24 nodes
  [nodes now have: risk_score (0-100)]

Time T=0:20 - Server Start
  $ python main.py
  ✓ FastAPI server started
  ✓ Listening on http://localhost:8000

Time T=0:25 - API Request
  $ curl http://localhost:8000/analyze-attack-vectors?graph=sim

Time T=0:30 - Red Agent
  ✓ Discovered schema
  ✓ Generated Cypher (Gemini)
  ✓ Found entry point: AUTH-03 (risk: 87)
  ✓ Generated attack narrative

Time T=0:35 - Response
  {
    "entry_point": "AUTH-03",
    "overall_severity": "CRITICAL",
    ...
  }

✅ SUCCESS: Entry point selected by risk_score, not hardcoded
```

---

## Environment Setup Check

Before running, verify:

```bash
# 1. Neo4j is running
curl http://localhost:7687  # Should connect (or appropriate port)

# 2. Python dependencies
python -c "import neo4j; print('neo4j OK')"
python -c "import google.generativeai; print('gemini OK')"

# 3. Configuration
cat backend/.env  # Check NEO4J_URI, GEMINI_API_KEY

# 4. Network connectivity
ping -c 1 example.com  # Internet (for NVD API if needed)
```

---

## Rollback / Reset

If you need to start over:

```bash
# Clear all calculated fields from Neo4j
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password>

# Then run:
MATCH (n)
REMOVE n.cvss_score
REMOVE n.exploit_available
REMOVE n.attack_vector
REMOVE n.cve_id
REMOVE n.cve_updated_at
REMOVE n.blast_radius_count
REMOVE n.risk_score
REMOVE n.risk_score_updated_at
RETURN count(n)

# Then re-run pipeline
python nvd_sync.py sim
python risk_calculator.py sim
```

---

## Summary: The Three Commands

**That's it. That's the pipeline.**

```bash
python nvd_sync.py sim              # Step 1: Real CVE data
python risk_calculator.py sim       # Step 2: Calculated scores
python main.py                      # Step 3: Ready to analyze
```

**Result:** Attack analysis driven by risk_score, not hardcoding. ✅
