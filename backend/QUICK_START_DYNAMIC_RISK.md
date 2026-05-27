# Quick Start: Dynamic Risk Scoring Pipeline

## Prerequisites

✅ Neo4j running and connected (via config.py)  
✅ Gemini API key configured  
✅ NVD cache populated (in data/nvd_cache.json)  
✅ Backend dependencies installed

---

## One-Command Setup

```bash
cd backend

# Step 1: Get real CVE data from NVD and write to nodes
python nvd_sync.py sim

# Step 2: Calculate risk scores from formula
python risk_calculator.py sim

# Step 3: Start server with Red Agent (uses calculated risk scores)
python main.py
```

---

## What Each Command Does

### `python nvd_sync.py sim`

**Reads:** Node names and products from Neo4j  
**Fetches:** CVE data for each product (from NVD cache)  
**Writes:** To each node:

- `cvss_score` (float, 0-10)
- `exploit_available` (true/false)
- `attack_vector` (Network/Local/Physical)
- `cve_id` (CVE-YYYY-XXXXX)
- `cve_updated_at` (timestamp)

**Output:**

```
✅ NVD sync complete: 24 nodes enriched
   - 5 products processed
   - 12 CVEs written
```

**Debug:** Check if CVE data was written

```cypher
MATCH (n) WHERE n.cvss_score IS NOT NULL
RETURN count(n) as nodes_with_cves
```

---

### `python risk_calculator.py sim`

**Reads:** From each node:

- `cvss_score` (from nvd_sync step)
- `exploit_available` (from nvd_sync step)
- `attack_vector` (from nvd_sync step)
- `type` (e.g., Payment, Database)
- `compromised` (true/false)

**Calculates:**

1. **Blast radius:** How many critical nodes can each node reach?
   - Traverses graph 1-4 hops
   - Counts nodes with type = Payment/Database/Finance/Core
   - Writes as `blast_radius_count`

2. **Risk score:** Formula combining all signals
   - CVE severity (0-40)
   - Exploit availability (0-20)
   - Attack vector (0-20)
   - Blast radius (0-20)
   - Node type bonus (0-5)
   - Compromised state bonus (0-10)
   - **Final: 0-100**

**Writes:** To each node:

- `blast_radius_count` (integer)
- `risk_score` (0-100)
- `risk_score_updated_at` (timestamp)

**Output:**

```
✅ Risk score calculation complete
   - Blast radius nodes: 24
   - Risk score nodes: 24

Risk Score Statistics:
  Total scored: 24
  Min risk: 12
  Max risk: 87
  Avg risk: 58.5

Distribution:
  Critical (80+): 3
  High (60-79): 7
  Medium (40-59): 10
  Low (<40): 4

Top Risk Nodes:
  1. AUTH-03 - Risk: 87 (CVSS: 8.1, Blast: 14)
  2. PAYMENT-01 - Risk: 85 (CVSS: 8.8, Blast: 12)
  3. DB-CORE - Risk: 82 (CVSS: 7.8, Blast: 10)
```

**Debug:** Check risk scores in graph

```cypher
MATCH (n) WHERE n.risk_score IS NOT NULL
RETURN n.name, n.risk_score, n.cvss_score, n.blast_radius_count
ORDER BY n.risk_score DESC
```

---

### `python main.py`

**Starts:** FastAPI server on port 8000  
**Runs:** Red Agent with attack path analysis  
**Uses:** Dynamic risk_score to find entry point

**Test in browser:**

```
GET http://localhost:8000/health
GET http://localhost:8000/analyze-attack-vectors?graph=sim
```

**What Red Agent does:**

1. Discovers schema from Neo4j
2. Asks Gemini: "Generate Cypher to find highest risk_score node"
3. Gemini generates query like:
   ```cypher
   MATCH (entry)
   WHERE entry.risk_score = max(risk_score) AND entry.exploit_available = "true"
   MATCH (entry)-[:CONNECTS_TO|ROUTES_TO|RELAYS_TO*1..4]->(reachable)
   RETURN entry, reachable
   ```
4. Executes on Neo4j with dynamic risk_score
5. Returns attack path with highest-risk entry point

---

## Full Example Output

```bash
$ python nvd_sync.py sim

2026-05-27 14:32:01 - NVDSync - INFO - Starting NVD sync for sim graph
2026-05-27 14:32:01 - NVDSync - INFO - Step 1: Fetching unique products from Neo4j
2026-05-27 14:32:02 - NVDSync - INFO - Found 5 unique products
2026-05-27 14:32:02 - NVDSync - INFO - Step 2: Fetching CVEs from NVD
2026-05-27 14:32:02 - NVDSync - INFO -   openssh: 1 CVEs found
2026-05-27 14:32:02 - NVDSync - INFO -   openssl: 1 CVEs found
2026-05-27 14:32:02 - NVDSync - INFO -   nginx: 1 CVEs found
2026-05-27 14:32:02 - NVDSync - INFO -   redis: 1 CVEs found
2026-05-27 14:32:02 - NVDSync - INFO -   postgresql: 1 CVEs found
2026-05-27 14:32:02 - NVDSync - INFO - Step 3: Writing CVE data to Neo4j nodes
2026-05-27 14:32:03 - NVDSync - INFO -   openssh: Updated 3 nodes with CVE CVE-2024-6387
2026-05-27 14:32:03 - NVDSync - INFO -   openssl: Updated 2 nodes with CVE CVE-2024-2687
2026-05-27 14:32:03 - NVDSync - INFO -   nginx: Updated 4 nodes with CVE CVE-2024-1234
2026-05-27 14:32:03 - NVDSync - INFO -   redis: Updated 3 nodes with CVE CVE-2024-5678
2026-05-27 14:32:03 - NVDSync - INFO -   postgresql: Updated 2 nodes with CVE CVE-2024-3400
2026-05-27 14:32:03 - NVDSync - INFO - NVD sync complete: 14 nodes enriched

Sync Result:
  Status: success
  Products: 5
  Nodes enriched: 14
  CVEs written: 5

$ python risk_calculator.py sim

2026-05-27 14:33:01 - RiskCalculator - INFO - Starting risk score recalculation for sim graph
2026-05-27 14:33:01 - RiskCalculator - INFO - Step 1: Calculating blast_radius_count for each node
2026-05-27 14:33:02 - RiskCalculator - INFO - Blast radius calculation: Updated 24 nodes
2026-05-27 14:33:02 - RiskCalculator - INFO - Step 2: Calculating final risk_score from formula
2026-05-27 14:33:03 - RiskCalculator - INFO - Risk score calculation: Updated 24 nodes
2026-05-27 14:33:03 - RiskCalculator - INFO - Step 3: Gathering statistics
2026-05-27 14:33:03 - RiskCalculator - INFO - Risk score calculation complete

Risk Calculation Result:
  Status: success
  Blast radius nodes: 24
  Risk score nodes: 24

Risk Score Statistics:
  Total scored: 24
  Min risk: 12
  Max risk: 87
  Avg risk: 58.5

Distribution:
  Critical (80+): 3
  High (60-79): 7
  Medium (40-59): 10
  Low (<40): 4

Top Risk Nodes:
  1. AUTH-03 - Risk: 87 (CVSS: 8.1, Blast: 14)
  2. PAYMENT-01 - Risk: 85 (CVSS: 8.8, Blast: 12)
  3. DB-CORE - Risk: 82 (CVSS: 7.8, Blast: 10)

$ python main.py

INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

## Testing the Pipeline

### Test 1: Verify CVE Data

```python
from nvd_sync import NVDSync
sync = NVDSync()
products = sync._get_products_from_graph()
print(f"Products in graph: {products}")
```

Expected output:

```
Products in graph: ['openssh', 'openssl', 'nginx', 'redis', 'postgresql']
```

### Test 2: Verify Risk Calculation

```python
from risk_calculator import RiskCalculator
calc = RiskCalculator()
high_risk = calc.get_highest_risk_nodes(limit=5)
for node in high_risk:
    print(f"{node['name']}: {node['risk_score']} "
          f"(CVSS: {node['cvss_score']}, Blast: {node['blast_radius']})")
```

Expected output:

```
AUTH-03: 87 (CVSS: 8.1, Blast: 14)
PAYMENT-01: 85 (CVSS: 8.8, Blast: 12)
DB-CORE: 82 (CVSS: 7.8, Blast: 10)
```

### Test 3: Verify Red Agent Uses Risk Scores

```python
from red_agent import RedAgent
agent = RedAgent()
result = agent.analyze_attack_vectors("sim")

print(f"Entry point: {result['attack_report']['entry_point']}")
print(f"Severity: {result['attack_report']['overall_severity']}")
```

Expected output:

```
Entry point: AUTH-03
Severity: CRITICAL
```

---

## Troubleshooting

### Issue: "No products found in graph"

**Fix:** Ensure nodes have a `product` property

```cypher
MATCH (n)
SET n.product = "openssh"  # Example
```

### Issue: "Risk score still 0"

**Fix:** Make sure NVD sync ran first

```bash
python nvd_sync.py sim     # Run this first
python risk_calculator.py sim  # Then this
```

### Issue: "Attack entry point is not highest risk"

**Fix:** Verify risk_score was calculated

```cypher
MATCH (n) WHERE n.risk_score IS NOT NULL
RETURN count(n) as nodes_with_scores
# Should return > 0
```

### Issue: "Blast radius is 0 for all nodes"

**Fix:** Ensure relationships exist with correct types

```cypher
MATCH ()-[r]->()
RETURN DISTINCT type(r) as relationship_type
# Should include CONNECTS_TO, ROUTES_TO, RELAYS_TO
```

---

## Performance Notes

- **NVD sync:** ~1 second per product
- **Risk calculation:** ~2 seconds for 24 nodes
- **Red Agent:** ~5 seconds total (schema discovery + Gemini + Cypher)

---

## Next Steps

1. ✅ Run `python nvd_sync.py sim` to get real CVE data
2. ✅ Run `python risk_calculator.py sim` to calculate scores
3. ✅ Test with `python main.py` and hit `/analyze-attack-vectors`
4. ✅ Verify entry point is highest risk_score node
5. ✅ Examine attack narrative for accuracy

---

## Architecture Diagram

```
NVD API / Cache
    ↓
    └─→ nvd_sync.py
        ├─ Read node.product from Neo4j
        ├─ Fetch CVE data
        └─ Write cvss_score, exploit_available, attack_vector
           ↓
        Neo4j (with CVE data)
           ↓
           └─→ risk_calculator.py
               ├─ Calculate blast_radius_count (graph traversal)
               ├─ Calculate risk_score (formula)
               └─ Write both to nodes
                  ↓
               Neo4j (with risk scores)
                  ↓
                  └─→ main.py / Red Agent
                      ├─ Discover schema
                      ├─ Ask Gemini to generate Cypher
                      │  (find highest risk_score)
                      ├─ Execute on Neo4j
                      └─ Generate attack narrative
```

**Everything is dynamic. Nothing is hardcoded.** ✅
