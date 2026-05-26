# QUICKSTART - Red Agent Backend

Get the Red Agent running in 5 minutes.

## What You're Getting

A production-grade **attack vector analysis engine** that:

- Reads server topology from Neo4j (single production server)
- Fetches real CVE data from NVD
- Uses Google Gemini LLM to prioritize attack vectors
- Calculates blast radius using graph traversal
- Returns human-executable remediation playbooks

```
Neo4j (Single Server) + NVD (CVEs) + Google Gemini = Caught U!
```

---

## Step 1: Prepare Environment (2 min)

### Get your credentials:

**Neo4j AuraDB:**

1. Go to https://console.neo4j.io
2. Create/select an AuraDB instance
3. Copy: URI, username, password

**Google Gemini API:**

1. Go to https://makersuite.google.com/app/apikey
2. Create API key
3. Ensure quota available

### Create .env file:

```bash
cp .env.example .env
```

**Edit `.env` and fill in:**

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
GEMINI_API_KEY=your-gemini-api-key-here
USE_CACHED_NVD=true
```

---

## Step 2: Install & Setup (2 min)

### On Windows:

```bash
startup.bat
```

### On macOS/Linux:

```bash
chmod +x startup.sh
./startup.sh
```

### Manual setup:

```bash
pip install -r requirements.txt
```

---

## Step 3: Import Neo4j Data (1 min)

Run these Cypher queries in your Neo4j Browser:

```cypher
// Copy CSV files to Neo4j import folder, then:

LOAD CSV WITH HEADERS FROM 'file:///nodes_server.csv' as row
CREATE (n:Server {graph: "prod"})
SET n = row;

LOAD CSV WITH HEADERS FROM 'file:///nodes_vulnerability.csv' as row
CREATE (n:Vulnerability {graph: "prod"})
SET n = row;

LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' as row
MATCH (a {name: row.from})
MATCH (b {name: row.to})
CREATE (a)-[:CONNECTS_TO]->(b);

// Create simulation graph copy
MATCH (n {graph: "prod"})
WITH n, labels(n) as lbls, properties(n) as props
CREATE (m) SET m = props SET m.graph = "sim";

MATCH (a {graph:"prod"})-[r]->(b {graph:"prod"})
MATCH (sa {graph:"sim", name:a.name})
MATCH (sb {graph:"sim", name:b.name})
CREATE (sa)-[:CONNECTS_TO]->(sb);
```

---

## Step 4: Run Red Agent

### Option A: Start FastAPI Server

```bash
python -m uvicorn main:app --reload
```

Visit: **http://localhost:8000/docs**

Then try:

```bash
curl -X POST http://localhost:8000/api/red-agent/analyze \
  -H "Content-Type: application/json" \
  -d '{"graph": "prod"}'
```

### Option B: Run Examples

```bash
python example_usage.py
```

Output shows:

- Top 3 attack vectors ranked by exploitability
- Affected servers
- Remediation strategies
- Business impact

### Option C: Direct Python

```python
from red_agent import run_red_agent_analysis

result = run_red_agent_analysis(graph_name="prod")
print(f"Attack vectors found: {len(result['attack_vectors'])}")
print(f"Top: {result['attack_vectors'][0]}")
```

---

## Demo: What You'll See

### Analysis Request:

```
Red Agent analyzes PRODUCTION graph...
  Step 1: Fetching servers ✓ (15 servers)
  Step 2: Fetching vulnerabilities ✓ (9 CVEs)
  Step 3: Enriching with NVD ✓
  Step 4: Calculating blast radius ✓
  Step 5: LLM prioritization ✓
```

### Results:

```json
{
  "status": "success",
  "servers_analyzed": 15,
  "vulnerabilities_found": 9,
  "attack_vectors": [
    {
      "rank": 1,
      "target_server": "AUTH-03",
      "target_ip": "10.0.2.3",
      "entry_cve": "CVE-2024-6387",
      "cvss_score": 8.1,
      "strategy": "Exploit OpenSSH regreSSHion RCE on AUTH-03...",
      "blast_radius": ["CBS-APP-01", "PAYMENT-GW", "SWIFT-NODE", "DB-CORE-01"],
      "exploitability_score": 9,
      "business_impact": "Compromise of payment processing and SWIFT"
    },
    ...
  ],
  "executive_summary": "AUTH-03 is the highest-risk attack vector...",
  "defensive_priorities": [
    "Patch OpenSSH on AUTH-03 to 9.2p1+",
    "Isolate AUTH-03 from untrusted networks",
    "Monitor AUTH-03 for suspicious behavior"
  ]
}
```

---

## API Endpoints

### Main: Analyze Attack Vectors

```bash
POST /api/red-agent/analyze
```

### Supporting Endpoints

```bash
GET /health                                    # Check if services are up
GET /api/red-agent/servers/prod               # List servers
GET /api/red-agent/vulnerabilities/prod       # List CVEs
GET /api/red-agent/blast-radius/prod/AUTH-03 # Blast radius
GET /api/red-agent/high-criticality-servers/prod
GET /api/red-agent/cves/openssh               # CVEs for product
```

Full API docs: **http://localhost:8000/docs** (when server running)

---

## Troubleshooting

### Neo4j Connection Error

```
Error: Neo4j connection failed
```

**Fix:**

- Verify credentials in `.env`
- Check AuraDB instance is running
- Test URI is accessible

### Gemini API Error

```
Error: API call failed
```

**Fix:**

- Get key from: https://makersuite.google.com/app/apikey
- Verify API key is valid and has quota
- Check `GEMINI_API_KEY` in `.env`

### No servers found

```
Error: No servers found in graph
```

**Fix:**

- Verify CSV files imported to Neo4j
- Check graph property matches ("prod" or "sim")
- Query Neo4j: `MATCH (n:Server) RETURN COUNT(n)`

### Import "main" error

```
ModuleNotFoundError: No module named 'main'
```

**Fix:**

- Ensure you're in backend/ directory
- Run: `python -m uvicorn main:app --reload`

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────┐
│                       RED AGENT FLOW                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Neo4j         2. NVD         3. LLM                     │
│     ┌─────┐         ┌────┐        ┌──────┐                 │
│     │  1  │ ──────> │ 9  │ ────> │Gemini│                 │
│     │Srvr │         │CVEs│        └──────┘                 │
│     └─────┘         └────┘          │                      │
│       │                             │                      │
│       └─────────── Merge ──────────┘                       │
│                      │                                     │
│                      ↓                                     │
│              Analysis Results:                            │
│         • Top 5 Attack Vectors (ranked)                   │
│         • Exploitability scores                           │
│         • Blast radius (affected nodes)                   │
│         • Remediation playbooks                           │
│                                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Files Explained

| File               | Purpose                               |
| ------------------ | ------------------------------------- |
| `config.py`        | Configuration & environment variables |
| `neo4j_client.py`  | Neo4j database operations             |
| `nvd_client.py`    | CVE data (cached for demo)            |
| `llm_client.py`    | Google Gemini API integration         |
| `red_agent.py`     | Main orchestration logic              |
| `main.py`          | FastAPI web server                    |
| `example_usage.py` | 7 runnable examples                   |
| `README.md`        | Full documentation                    |
| `.env`             | Your credentials (DO NOT COMMIT)      |

See `FILE_STRUCTURE.md` for detailed breakdown.

---

## Next Steps

1. ✅ Setup complete — Red Agent is ready
2. 📊 Frontend integration — Call `/api/red-agent/analyze` from React
3. 🔵 Blue Agent — Generates remediation (separate module)
4. 🟣 LangGraph — State machine for simulation loop
5. 📈 Scale up — Add UEBA, compliance agent, reporter agent

---

## Demo Day Tips

**Show judges:**

1. **Live Analysis** — Run `/api/red-agent/analyze` on production graph
   - "Here's the current threat landscape"

2. **Blast Radius** — Query `get_blast_radius` for AUTH-03
   - "6 nodes at risk if this server compromised"

3. **CVE Details** — Call `get_cves/openssh`
   - "Real CVE data from NVD, integrated with topology"

4. **Playbook** — Generate `remediation_playbook` for top vector
   - "Human-executable steps, not code"

5. **Highlight**:
   - "No other team will have Neo4j blast radius visualization"
   - "We use real bank topology + real CVEs + real LLM analysis"

---

**Questions?** Check `README.md` or `example_usage.py`

**Ready to code?** Start with `main.py` for API routes or `red_agent.py` for logic.

Good luck at PSBs Hackathon 2026! 🚀
