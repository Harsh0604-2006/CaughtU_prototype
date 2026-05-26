# Red Agent Backend - Caught U!

Generative AI-powered attack vector analysis for banking cybersecurity.

## Architecture

The Red Agent orchestrates three data sources:

```
Neo4j (Servers)  +  NVD API (CVEs)  +  Google Gemini LLM  →  Prioritized Attack Vectors
```

### Components

1. **Neo4j Client** (`neo4j_client.py`)
   - Connects to Neo4j AuraDB
   - Fetches server nodes (product, version, IP, criticality)
   - Single production server (simulated)
   - Calculates blast radius using Cypher traversal
   - Retrieves vulnerabilities from graph relationships

2. **NVD Client** (`nvd_client.py`)
   - Pre-cached CVE data for banking products (OpenSSH, OpenSSL, Nginx, etc.)
   - For demo: uses cached JSON to avoid rate limits and Wi-Fi issues
   - For production: can fetch from NVD API nightly
   - Includes CVSS scores, attack vectors, exploit availability

3. **LLM Client** (`llm_client.py`)
   - Google Gemini API integration (gemini-1.5-pro)
   - Prioritizes attack vectors by: exploitability × CVSS × criticality × blast radius
   - Generates human-executable remediation playbooks
   - Returns structured JSON output

4. **Red Agent** (`red_agent.py`)
   - Orchestrates the three data sources
   - Analyzes attack vectors end-to-end
   - Identifies high-risk servers
   - Enriches vulnerability data

5. **FastAPI Server** (`main.py`)
   - REST API for Red Agent
   - Health checks
   - Server listing
   - Vulnerability retrieval
   - Blast radius calculation
   - CVE lookup
   - Playbook generation

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the backend folder:

```env
# Neo4j Configuration
NEO4J_URI=neo4j+s://your-auradb-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here

# Google Gemini LLM Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# NVD Configuration (use cached data for demo)
NVD_API_KEY=your_nvd_api_key_here
USE_CACHED_NVD=true
NVD_CACHE_PATH=data/nvd_cache.json

# Graph names
SIMULATION_GRAPH=sim
PRODUCTION_GRAPH=prod
```

### 3. Neo4j Graph Setup (One-time)

Before running the Red Agent, import the CSV files into Neo4j:

```bash
# In Neo4j Browser, run:

// Import Nodes
:auto LOAD CSV WITH HEADERS FROM 'file:///nodes_bank.csv' as row
CREATE (n:Bank {graph: "prod"})
SET n = row;

:auto LOAD CSV WITH HEADERS FROM 'file:///nodes_server.csv' as row
CREATE (n:Server {graph: "prod"})
SET n = row;

:auto LOAD CSV WITH HEADERS FROM 'file:///nodes_vulnerability.csv' as row
CREATE (n:Vulnerability {graph: "prod"})
SET n = row;

// Import Relationships
:auto LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' as row
MATCH (a {name: row.from})
MATCH (b {name: row.to})
CREATE (a)-[:CONNECTS_TO]->(b);

// Create simulation graph copy
MATCH (n {graph: "prod"})
WITH n, labels(n) as lbls, properties(n) as props
CREATE (m) SET m = props SET m.graph = "sim"
SET m.compromised = false;

MATCH (a {graph:"prod"})-[r]->(b {graph:"prod"})
MATCH (sa {graph:"sim", name:a.name})
MATCH (sb {graph:"sim", name:b.name})
CREATE (sa)-[:CONNECTS_TO]->(sb);
```

## Running the Red Agent

### Option 1: Start FastAPI Server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

### Option 2: Direct Python Usage

```python
from red_agent import run_red_agent_analysis
from config import PRODUCTION_GRAPH

# Run analysis
result = run_red_agent_analysis(graph_name=PRODUCTION_GRAPH)

# Print results
print(f"Servers Analyzed: {result['servers_analyzed']}")
print(f"Vulnerabilities Found: {result['vulnerabilities_found']}")
print(f"Top Attack Vector: {result['attack_vectors'][0] if result['attack_vectors'] else 'None'}")
```

## API Endpoints

### Health Check

```
GET /health
```

### Analyze Attack Vectors (Main endpoint)

```
POST /api/red-agent/analyze
Content-Type: application/json

{
  "graph": "prod",
  "focus_server": null
}
```

Response:

```json
{
  "status": "success",
  "graph": "prod",
  "servers_analyzed": 15,
  "vulnerabilities_found": 9,
  "high_risk_servers": [...],
  "attack_vectors": [
    {
      "rank": 1,
      "target_server": "AUTH-03",
      "target_ip": "10.0.2.3",
      "entry_cve": "CVE-2024-6387",
      "cvss_score": 8.1,
      "strategy": "Exploit OpenSSH regreSSHion RCE...",
      "blast_radius": ["CBS-APP-01", "PAYMENT-GW", ...],
      "exploitability_score": 9,
      "business_impact": "..."
    }
  ],
  "executive_summary": "AUTH-03 is the highest-risk server...",
  "defensive_priorities": ["Patch OpenSSH on AUTH-03", ...]
}
```

### Get Servers

```
GET /api/red-agent/servers/prod
```

### Get Vulnerabilities

```
GET /api/red-agent/vulnerabilities/prod
```

### Get Blast Radius

```
GET /api/red-agent/blast-radius/prod/AUTH-03
```

### Get High-Criticality Servers

```
GET /api/red-agent/high-criticality-servers/prod
```

### Get CVEs for Product

```
GET /api/red-agent/cves/openssh
```

### Generate Remediation Playbook

```
POST /api/red-agent/remediation-playbook
Content-Type: application/json

{
  "attack_vector": {...},
  "server_properties": {...}
}
```

## Demo Scenario: AUTH-03 Attack Chain

### Attack Vector Identified

- **Target**: AUTH-03 (Authentication Server, IP 10.0.2.3, CRITICAL)
- **Vulnerability**: CVE-2024-6387 (OpenSSH regreSSHion, CVSS 8.1)
- **Blast Radius**: 6 nodes (CBS-APP-01 → PAYMENT-GW → SWIFT-NODE → DB-CORE-01 → DB-TXNLOG-01)
- **Exploit**: Pre-auth RCE, no special privileges needed
- **Impact**: Compromise of payment processing and SWIFT communication

### LLM Analysis

Gemini prioritizes this attack because:

1. **High Exploitability** (9/10): CVE-2024-6387 is actively exploited, no auth required
2. **Critical CVSS** (8.1): High impact on CIA triad
3. **Critical Server** (Criticality=CRITICAL): AUTH-03 handles all bank authentication
4. **Large Blast Radius** (6 nodes affected): Can reach SWIFT node and payment systems
5. **Exploit Available**: Real-world exploit code exists

### Remediation Playbook Generated

The LLM generates:

```
Step 1 (IMMEDIATE, 5 min): Isolate AUTH-03 from internal network
  - Action: Block port 22 at firewall
  - Verify: Confirm auth-03 unreachable via SSH
  - Team: Network Operations

Step 2 (SHORT-TERM, 15 min): Upgrade OpenSSH
  - Action: Install OpenSSH 9.2p1 or later
  - Verify: Confirm sshd version with -V flag
  - Team: Infrastructure / DevOps

Step 3 (SHORT-TERM, 10 min): Rebuild AUTH-03 from golden image
  - Action: Restore from known-good snapshot
  - Verify: Run security baseline compliance checks
  - Team: Infrastructure

Step 4 (LONG-TERM, 30 min): Enable continuous vulnerability scanning
  - Action: Deploy CVSS monitoring for all servers
  - Team: Security Engineering

Total time: 1 hour
Risk before: Critical
Risk after: Low
```

## Data Files

Pre-generated CSV files for Neo4j import (in `neo4j/` folder):

- `nodes_bank.csv` — Bank entity
- `nodes_branch.csv` — 10 branches
- `nodes_customer.csv` — 12 customers
- `nodes_account.csv` — 16 accounts
- `nodes_transaction.csv` — 15 transactions (4 flagged)
- `nodes_loan.csv` — 12 loans
- `nodes_employee.csv` — 15 employees
- `nodes_server.csv` — 15 servers (KEY DATA)
- `nodes_vulnerability.csv` — 9 CVEs
- `nodes_incident.csv` — 5 incidents
- `relationships.csv` — All edges

## Demo Flow

```
1. Frontend "Run Simulation" button clicked
2. LangGraph orchestrator calls Red Agent on SIM graph
3. Red Agent analyzes: AUTH-03 has CVE-2024-6387 (CVSS 8.1, exploitable)
4. LLM prioritizes: "AUTH-03 is the #1 attack vector"
5. Blast radius calculated: 6 nodes affected
6. Blue Agent (not shown here) generates remediation playbook
7. Human (analyst) reviews and approves
8. Fix applied to SIM graph (simulate patch)
9. Retest: Blast radius now just AUTH-03 itself
10. Result displayed: "Vulnerability mitigated"
```

## Key Features

✅ **Single Production Server Setup**: Simulated in Neo4j for demo  
✅ **Google Gemini Integration**: Using gemini-1.5-pro for intelligent analysis  
✅ **Dual-Loop Design**: Simulation vs. Live Defence  
✅ **Human-in-the-Loop**: Analyst approval before fixes  
✅ **Neo4j Blast Radius**: Graph traversal finds all affected nodes  
✅ **Real CVE Data**: NVD integration with pre-cached JSON for demo  
✅ **LLM Prioritization**: Gemini ranks by exploitability × impact  
✅ **Playbook Generation**: Human-executable steps, not code  
✅ **Production-Ready**: Designed for RBI compliance + PSB use

## Troubleshooting

### Neo4j Connection Failed

- Check credentials in `.env`
- Verify AuraDB instance is running
- Test: `curl https://your-instance.databases.neo4j.io`

### Gemini API Key Invalid

- Get API key from: https://makersuite.google.com/app/apikey
- Verify key is valid and has quota
- Check `GEMINI_API_KEY` in `.env`

### NVD Cache Not Loading

- Check `data/nvd_cache.json` exists and is valid JSON
- Verify `NVD_CACHE_PATH` in `.env` is correct

### Blast Radius Returns Empty

- Verify relationships exist between servers in Neo4j
- Run: `MATCH (a)-[r:CONNECTS_TO]->(b) RETURN COUNT(r)` in Neo4j Browser

## Performance Notes

- Server fetch: ~100ms (Neo4j)
- Vulnerability fetch: ~50ms (Neo4j join)
- NVD enrichment: ~200ms (cached lookup)
- LLM analysis: ~2-3 seconds (Gemini API)
- Blast radius: ~150ms (Cypher traversal, 5 hops)
- **Total**: ~3 seconds end-to-end

For production with thousands of servers, add:

- Redis caching for server lists
- Batch vulnerability processing
- Scheduled NVD syncs (nightly)
- Async LLM calls via Celery

## For Judges (PSBs Hackathon)

**Key Innovation**: Neo4j graph traversal for realistic blast radius calculation  
**Differentiator**: Combines topology (graph) + vulnerabilities (NVD) + intelligence (LLM)  
**Compliance**: Human-in-the-loop design aligns with RBI cybersecurity guidelines  
**Scalability**: Designed for 1000+ node networks (demo shows 15 nodes)  
**Real-World**: Modeled after 2016 Union Bank SWIFT hack attack chain

---

Built for **IDEA 2.0 Hackathon** by TRUST ISSUES team  
Mentor: Union Bank of India + IBA
