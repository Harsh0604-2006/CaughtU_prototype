# Red Agent Backend - File Structure

## Overview

The Red Agent backend is a Python FastAPI application that orchestrates attack vector analysis for the Caught U! cybersecurity platform.

**Data Flow:**

```
Neo4j (Topology) → NVD (CVEs) → LLM (Intelligence) → Attack Vectors
```

---

## Core Modules

### 1. **config.py**

Central configuration management. Loads all environment variables and provides constants.

**Key exports:**

- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` — Neo4j connection
- `GEMINI_API_KEY`, `GEMINI_MODEL` — Google Gemini LLM configuration
- `PRODUCTION_GRAPH`, `SIMULATION_GRAPH` — Graph names
- `CVSS_THRESHOLD`, `MAX_ATTACK_VECTORS` — Analysis thresholds

### 2. **neo4j_client.py**

Neo4j database client. Handles all graph database operations.

**Key methods:**

- `get_servers(graph_name)` — Fetch all server nodes with properties
- `get_vulnerabilities_for_servers(servers)` — Get CVEs affecting servers
- `get_blast_radius(server_name)` — Calculate lateral movement impact (Cypher traversal)
- `get_high_criticality_servers(graph_name)` — Filter by CRITICAL/HIGH severity
- `check_connection()` — Verify Neo4j is accessible

**Used by:** Red Agent, FastAPI endpoints

### 3. **nvd_client.py**

NVD (National Vulnerability Database) client. Pre-caches CVE data for demo.

**Key methods:**

- `get_cves_for_product(product, version)` — Fetch CVEs for product
- `_get_cves_from_cache()` — Use pre-cached JSON (demo mode)
- `_fetch_cves_from_api()` — Fetch from NVD API live (production)

**Demo CVE Data Included:**

- OpenSSH (regreSSHion)
- OpenSSL
- Nginx
- Redis
- PostgreSQL
- Java
- Linux Kernel
- Apache HTTP Server

**Used by:** Red Agent, FastAPI endpoints

### 4. **llm_client.py**

Google Gemini LLM client (gemini-1.5-pro). Generates intelligent analysis and remediation playbooks.

**Key methods:**

- `prioritize_attack_vectors(servers, vulnerabilities, blast_radius)` — Main analysis
  - Input: Neo4j servers + NVD CVEs + blast radius
  - Output: Ranked attack vectors by exploitability
  - LLM criteria: exploitability × CVSS × criticality × blast radius
- `generate_remediation_playbook(attack_vector, server_properties)` — Blue Agent output
  - Input: Identified attack vector
  - Output: Human-executable remediation steps (not code)

**Used by:** Red Agent

### 5. **red_agent.py**

Main Red Agent orchestrator. Combines all sources for attack vector analysis.

**Key methods:**

- `analyze_attack_vectors(graph_name)` — Entry point
  - Step 1: Fetch servers from Neo4j
  - Step 2: Get vulnerabilities
  - Step 3: Enrich with NVD data
  - Step 4: Calculate blast radius
  - Step 5: LLM prioritization
  - Step 6: Format output

- `_enrich_vulnerabilities()` — Merge Neo4j + NVD data
- `_calculate_blast_radii()` — Graph traversal for each high-risk server
- `_identify_high_risk_servers()` — Risk scoring (CVSS × criticality × exploit)

**Used by:** FastAPI, Example scripts

---

## API Layer

### 6. **main.py**

FastAPI server. REST API for Red Agent functionality.

**Core endpoints:**

| Endpoint                                          | Method | Purpose                                       |
| ------------------------------------------------- | ------ | --------------------------------------------- |
| `/health`                                         | GET    | Service health check (Neo4j, NVD, LLM status) |
| `/api/red-agent/analyze`                          | POST   | Main attack vector analysis                   |
| `/api/red-agent/servers/{graph}`                  | GET    | List servers                                  |
| `/api/red-agent/vulnerabilities/{graph}`          | GET    | List vulnerabilities                          |
| `/api/red-agent/blast-radius/{graph}/{server}`    | GET    | Calculate blast radius                        |
| `/api/red-agent/high-criticality-servers/{graph}` | GET    | High-risk servers                             |
| `/api/red-agent/cves/{product}`                   | GET    | CVEs for product                              |
| `/api/red-agent/remediation-playbook`             | POST   | Generate playbook                             |

**Run:**

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**API Docs:** `http://localhost:8000/docs`

---

## Configuration & Setup

### 7. **.env.example**

Template for environment variables.

**Copy to .env and fill in:**

```bash
cp .env.example .env
```

**Required variables:**

- `NEO4J_URI` — Your AuraDB instance URI
- `NEO4J_USERNAME` — Usually "neo4j"
- `NEO4J_PASSWORD` — Your password
- `GEMINI_API_KEY` — Google Gemini API key

### 8. **requirements.txt**

Python package dependencies.

**Key packages:**

- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `neo4j` — Graph database driver
- `google-generativeai` — Google Gemini API client
- `pydantic` — Data validation
- `python-dotenv` — Environment variable loading

**Install:**

```bash
pip install -r requirements.txt
```

### 9. **startup.sh** (Linux/macOS)

Automated startup script with checks.

**What it does:**

1. Verifies Python installation
2. Checks .env file exists
3. Creates data/ directory
4. Installs dependencies
5. Tests Neo4j connection
6. Provides startup instructions

**Run:**

```bash
chmod +x startup.sh
./startup.sh
```

### 10. **startup.bat** (Windows)

Windows equivalent of startup.sh

**Run:**

```batch
startup.bat
```

---

## Documentation & Examples

### 11. **README.md**

Comprehensive guide covering:

- Architecture overview
- Component descriptions
- Setup instructions
- API endpoints with examples
- Demo scenario walkthrough
- Troubleshooting
- Performance notes
- Production scalability tips

### 12. **example_usage.py**

Seven runnable examples demonstrating all features:

1. **Basic Analysis** — Full attack vector analysis
2. **Simulation Graph** — Analysis on testing graph
3. **Servers & Vulns** — Fetch individually
4. **Blast Radius** — Lateral movement impact
5. **CVE Lookup** — Product-specific CVEs
6. **High-Risk Servers** — Ranking servers by risk
7. **Demo Scenario** — AUTH-03 attack chain walkthrough

**Run:**

```bash
python example_usage.py
```

---

## Data & Graph

### 13. **data/** (Directory)

Pre-cached CVE and analysis data.

**Contents:**

- `nvd_cache.json` — Pre-cached CVE data (auto-generated)
- Later: Redis cache, analysis history

---

## File Dependency Graph

```
main.py (FastAPI Server)
├── config.py
├── red_agent.py
│   ├── neo4j_client.py
│   │   └── config.py
│   ├── nvd_client.py
│   │   └── config.py
│   └── llm_client.py
│       └── config.py
└── requirements.txt

example_usage.py
└── red_agent.py
    └── (all above)

startup.sh / startup.bat
├── requirements.txt
└── neo4j_client.py
```

---

## Execution Flow

### Demo: "Run Simulation" Button

```
1. Frontend calls: POST /api/red-agent/analyze?graph=sim

2. main.py routes to red_agent.analyze_attack_vectors("sim")

3. red_agent.py:
   a) Calls neo4j_client.get_servers("sim")
      → Returns 15 servers with product/version/criticality

   b) Calls neo4j_client.get_vulnerabilities_for_servers()
      → Returns 9 CVEs from Neo4j relationships

   c) Enriches with nvd_client.get_cves_for_product()
      → Merges CVSS, attack vectors, exploit status

   d) Calls neo4j_client.get_blast_radius() for each high-risk server
      → Cypher: START from server → traverse 5 hops → return affected nodes
      → Example: AUTH-03 → 6 nodes affected

   e) Calls llm_client.prioritize_attack_vectors()
      → Prompts Gemini: "Given servers + vulns + blast_radius, rank by exploitability"
      → Gemini returns JSON with top 3-5 attack vectors
      → Includes strategy, blast radius, business impact

4. Format result:
   - attack_vectors: [rank, target, cve, cvss, strategy, blast_radius, ...]
   - executive_summary: "AUTH-03 is highest risk because..."
   - defensive_priorities: ["Patch OpenSSH", "Isolate AUTH-03", ...]

5. Frontend displays:
   - Ranked attack vectors
   - Blast radius visualization on graph
   - Blue Agent playbook button
```

---

## Key Differentiators for Judges

✅ **Single Production Server** — Optimized demo with representative topology  
✅ **Neo4j Blast Radius** — Uses real graph traversal (unlike text-based tools)  
✅ **Dual-Loop Design** — Simulation (SIM) vs Live (PROD) graphs  
✅ **Human-in-the-Loop** — LangGraph interrupts for analyst approval  
✅ **Real CVE Data** — Integrates with NVD API (pre-cached for demo)  
✅ **LLM Intelligence** — Google Gemini prioritizes by multiple factors  
✅ **Playbook Generation** — Human-executable steps (compliance-ready)  
✅ **Production-Ready** — Designed for RBI guidelines + PSB banking

---

## Quick Start

```bash
# 1. Setup
cp .env.example .env
# (Edit .env with your credentials)

# 2. Install
pip install -r requirements.txt

# 3. Start
python -m uvicorn main:app --reload

# 4. Visit
# http://localhost:8000/docs

# 5. Or run examples
python example_usage.py
```

---

Built for **PSBs Hackathon 2026 - IDEA 2.0** by **TRUST ISSUES** team
