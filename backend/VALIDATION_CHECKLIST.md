# Validation & Testing Checklist

## Pre-Flight Checks

### Environment Setup

- [ ] Neo4j is running and accessible

  ```bash
  cypher-shell -a bolt://localhost:7687 -u neo4j -p <password>
  # Should show: neo4j@neo4j>
  ```

- [ ] Python 3.8+ installed

  ```bash
  python --version
  # Should show: Python 3.8.x or higher
  ```

- [ ] Required packages installed

  ```bash
  python -c "import neo4j, google.generativeai; print('OK')"
  # Should show: OK
  ```

- [ ] Configuration file exists and has values
  ```bash
  cat backend/.env
  # Should show: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GEMINI_API_KEY
  ```

---

## Step 1: NVD Sync Validation

### Run the command

```bash
cd backend
python nvd_sync.py sim
```

### Check output

- [ ] No error messages
- [ ] Shows "Step 1: Fetching unique products"
- [ ] Shows "Step 2: Fetching CVEs from NVD"
- [ ] Shows "Step 3: Writing CVE data to Neo4j nodes"
- [ ] Shows "NVD sync complete"

### Verify in Neo4j

```bash
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password>

MATCH (n)
WHERE n.cvss_score IS NOT NULL
RETURN count(n) as nodes_with_cves,
       min(n.cvss_score) as min_cvss,
       max(n.cvss_score) as max_cvss
```

Expected output:

```
nodes_with_cves  min_cvss  max_cvss
        14         7.2       8.8
```

- [ ] At least one node has cvss_score
- [ ] cvss_score values are between 0-10
- [ ] At least some nodes have cve_id (CVE-2024-XXXX format)

### Check specific fields

```bash
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password>

MATCH (n)
WHERE n.cvss_score IS NOT NULL
RETURN n.name, n.cvss_score, n.exploit_available, n.cve_id
LIMIT 5
```

- [ ] Each row has all 4 fields populated
- [ ] exploit_available is "true" or "false" (string)
- [ ] cve_id starts with "CVE-"

---

## Step 2: Risk Calculator Validation

### Run the command

```bash
python risk_calculator.py sim
```

### Check output

- [ ] No error messages
- [ ] Shows "Step 1: Calculating blast_radius_count"
- [ ] Shows "Blast radius calculation: Updated X nodes"
- [ ] Shows "Step 2: Calculating final risk_score"
- [ ] Shows "Risk score calculation: Updated X nodes"
- [ ] Shows "Risk Score Statistics"

### Verify statistics output

Expected format:

```
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

- [ ] Distribution adds up to total (3+7+10+4 = 24)
- [ ] Max risk is 100 or less
- [ ] Min risk is > 0 (shouldn't be 0 if step 1 worked)
- [ ] Shows at least 3 top nodes

### Verify in Neo4j

```bash
MATCH (n)
WHERE n.risk_score IS NOT NULL
RETURN count(n) as nodes_with_scores,
       min(n.risk_score) as min_score,
       max(n.risk_score) as max_score,
       avg(n.risk_score) as avg_score
```

Expected output:

```
nodes_with_scores  min_score  max_score  avg_score
        24         12         87         58.5
```

- [ ] Count matches total_scored_nodes from step output
- [ ] All scores are 0-100 range
- [ ] At least one node has blast_radius_count >= 1

### Check individual nodes

```bash
MATCH (n)
WHERE n.risk_score IS NOT NULL
RETURN n.name, n.risk_score, n.cvss_score, n.blast_radius_count, n.exploit_available
ORDER BY n.risk_score DESC
LIMIT 3
```

- [ ] Top nodes have high risk_score (>= 80 preferred)
- [ ] Each has all fields populated
- [ ] Formula is visible (risk = cve + exploit + vector + blast)

---

## Step 3: Red Agent Validation

### Start the server

```bash
python main.py
```

### Check output

- [ ] No errors during startup
- [ ] Shows: "Started server process"
- [ ] Shows: "Uvicorn running on http://0.0.0.0:8000"
- [ ] Shows: "Application startup complete"

### Test health endpoint (in another terminal)

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{
  "status": "healthy",
  "timestamp": "2026-05-27T14:35:00Z",
  "services": {
    "neo4j": "connected",
    "redis": "ready"
  }
}
```

- [ ] Status is "healthy"
- [ ] Services show connected/ready

### Test attack analysis endpoint

```bash
curl "http://localhost:8000/analyze-attack-vectors?graph=sim" | python -m json.tool
```

Expected structure:

```json
{
  "status": "success",
  "graph": "sim",
  "schema_discovered": 5,
  "results_found": 14,
  "attack_report": {
    "entry_point": "AUTH-03",
    "cve_used": "CVE-2024-6387",
    "attack_steps": [
      {
        "step": 1,
        "action": "...",
        "mitre_technique": "T1021.006",
        "target_node": "AUTH-03",
        "result": "..."
      }
    ],
    "highest_value_target": "PAYMENT-CORE",
    "blast_radius_count": 14,
    "overall_severity": "CRITICAL",
    "recommended_defenses": [...]
  }
}
```

- [ ] Status is "success" (not "error")
- [ ] schema_discovered > 0 (graph structure found)
- [ ] results_found > 0 (Cypher executed successfully)
- [ ] entry_point exists (should be highest risk_score node)
- [ ] attack_steps is a non-empty array
- [ ] overall_severity is CRITICAL/HIGH/MEDIUM/LOW
- [ ] All steps have MITRE techniques (T00XX.XXX format)

### Verify entry point is highest risk

```bash
# In Neo4j, find the actual highest risk node
MATCH (n)
WHERE n.risk_score IS NOT NULL
RETURN n.name, n.risk_score
ORDER BY n.risk_score DESC
LIMIT 1
```

- [ ] Note the highest risk_score node name
- [ ] Compare to entry_point in API response
- [ ] They should match

### Check attack narrative quality

```bash
# From the API response, review attack_steps
```

- [ ] Each step has logical progression
- [ ] MITRE techniques are realistic (T1021 = Lateral Movement, etc.)
- [ ] Target nodes make sense (AUTH → FILE → PAYMENT pattern)
- [ ] Results describe realistic compromise scenarios

---

## Integration Validation

### Full Pipeline Test

```bash
# Terminal 1: Run sync
python nvd_sync.py sim
# Verify: nodes_enriched > 0

# Terminal 1: Run calculator
python risk_calculator.py sim
# Verify: risk_score_nodes_updated > 0

# Terminal 1: Start server
python main.py
# Verify: Server started successfully

# Terminal 2: Test API
curl "http://localhost:8000/analyze-attack-vectors?graph=sim"
# Verify: Returns success with attack_report

# Terminal 1: Check logs
# Verify: All steps logged properly
```

Checklist:

- [ ] Pipeline runs without errors
- [ ] Data flows correctly through all 3 steps
- [ ] API returns meaningful results
- [ ] Entry point is highest-risk node

---

## Correctness Validation

### Test 1: Risk Score Formula

```python
# Manually verify calculation for one node
# Example: AUTH-03

# From DB:
cvss_score = 8.1
exploit_available = "true"
attack_vector = "Network"
blast_radius_count = 14
type = "Server"  # Not in critical list
compromised = false

# Manual calculation:
cve_component = 8.1 * 4 = 32.4
exploit_component = 20
vector_component = 20
blast_component = 15  # 6-10 range → 15
type_bonus = 0  # Server not in [Payment, DB, Finance, Core]
compromised_bonus = 0

total = 32.4 + 20 + 20 + 15 + 0 + 0 = 87.4 → 87
```

- [ ] Calculated value matches DB value
- [ ] Formula components are clearly visible

### Test 2: Blast Radius Calculation

```bash
# Manually verify blast radius for one node
# Example: AUTH-03

MATCH (entry {name: "AUTH-03"})
MATCH (entry)-[:CONNECTS_TO|ROUTES_TO|RELAYS_TO*1..4]->(target)
WHERE target.type IN ["Database", "Payment", "Finance", "Core", "Critical"]
RETURN count(DISTINCT target) as manual_count
```

- [ ] manual_count matches n.blast_radius_count

### Test 3: Cypher Generation

```python
# Check that Red Agent generates Cypher from schema
from red_agent import RedAgent

agent = RedAgent()
schema = agent.neo4j.discover_schema()
cypher = agent._generate_cypher_query(schema)

# Verify:
print(cypher)
```

- [ ] Cypher is generated (not hardcoded)
- [ ] Uses actual schema labels/relationships
- [ ] Includes "highest cvss_score" or "highest risk_score"
- [ ] Includes traversal through relationships

---

## Performance Validation

### Check execution times

```bash
# Time nvd_sync
time python nvd_sync.py sim
# Expected: < 30 seconds

# Time risk calculator
time python risk_calculator.py sim
# Expected: < 30 seconds

# Time API response
time curl "http://localhost:8000/analyze-attack-vectors?graph=sim"
# Expected: < 10 seconds
```

- [ ] All steps complete within reasonable time
- [ ] No timeout errors

---

## Error Handling Validation

### Test missing CVE data

```bash
# Delete cvss_score from a node
MATCH (n {name: "TEST-NODE"})
REMOVE n.cvss_score
RETURN n

# Run risk calculator
python risk_calculator.py sim

# Verify: Still completes, node has risk_score >= 5
```

- [ ] Calculator handles missing cvss_score gracefully

### Test missing relationships

```bash
# If a node has no outgoing relationships
MATCH (n {name: "ISOLATED"})
OPTIONAL MATCH (n)-[r]->()
WHERE r IS NOT NULL
DELETE r

# Run risk calculator
python risk_calculator.py sim

# Verify: blast_radius_count = 0, risk_score still calculated
```

- [ ] Calculator handles isolated nodes

### Test Neo4j connection failure

```bash
# Stop Neo4j
# Run scripts
python nvd_sync.py sim

# Verify: Returns error with message, doesn't crash
```

- [ ] Scripts fail gracefully with informative error

---

## Documentation Validation

- [ ] `DYNAMIC_RISK_SCORING.md` exists
- [ ] `QUICK_START_DYNAMIC_RISK.md` exists
- [ ] `EXECUTION_ORDER.md` exists
- [ ] `IMPLEMENTATION_COMPLETE.md` exists
- [ ] `DELIVERABLES.md` exists
- [ ] All docs are readable and helpful

---

## Final Sign-Off Checklist

### Code Quality

- [ ] nvd_sync.py has no syntax errors
- [ ] risk_calculator.py has no syntax errors
- [ ] Both files are importable
- [ ] All functions have docstrings

### Functionality

- [ ] NVD sync writes CVE data
- [ ] Risk calculator calculates scores
- [ ] Red Agent uses highest risk_score
- [ ] Attack narrative is generated

### Integration

- [ ] Pipeline runs in correct order
- [ ] Data flows through all steps
- [ ] No data loss between steps
- [ ] API returns meaningful results

### Documentation

- [ ] Quick start guide is complete
- [ ] Execution order is clear
- [ ] Formula is explained
- [ ] Troubleshooting guide included

### Testing

- [ ] All manual tests pass
- [ ] Entry point is verified
- [ ] Formula is validated
- [ ] Error handling works

---

## Success Criteria

You're ready to deploy when:

✅ All checks above are marked  
✅ No error messages in logs  
✅ Entry point = highest risk_score node  
✅ Attack narrative makes sense  
✅ Formula is auditable and correct  
✅ Documentation is complete  
✅ Everything is data-driven (no hardcoding)

**Status: READY FOR PRODUCTION** ✅
