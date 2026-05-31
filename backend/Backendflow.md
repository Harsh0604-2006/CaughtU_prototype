Red_agent

Neo4j node properties
(os_product, os_version)
↓
nvd_sync.py → NVD API
↓
CVE written to node
(cve_id, cvss_score,
exploit_available)
↓
risk_calculator.py
↓
risk_score on each node
↓
Red Agent reads schema
(no hardcoded labels)
↓
Gemini generates Cypher
↓
Cypher runs on Neo4j
(finds highest risk node,
traverses CONNECTS_TO)
↓
Gemini interprets results
↓
Attack report JSON

---

Blue Agent

Red Agent report

- server properties
- risk context
  ↓
  Gemini generates playbook
  ↓
  Human reviews + approves
  ↓
  apply_fix() runs Cypher
  DELETE all edges on node
  SET status = Isolated
  ↓
  risk_calculator re-runs
  ↓
  risk_score drops
  ↓
  Retest blast radius
  (fewer nodes reachable)
  ↓
  Fix verified

How can we assure that our backend is not hardcoded data
