// ── api.js — All Neo4j + Backend Calls ──────────────────────
// Connects directly to Neo4j Aura using neo4j-driver
import neo4j from "neo4j-driver";

const URI      = import.meta.env.VITE_NEO4J_URI;
const USER     = import.meta.env.VITE_NEO4J_USER;
const PASSWORD = import.meta.env.VITE_NEO4J_PASSWORD;

console.log("URI:", URI);
console.log("USER:", USER);
console.log("PASSWORD exists:", !!PASSWORD);

const driver = neo4j.driver(URI, neo4j.auth.basic(USER, PASSWORD));

async function runQuery(cypher, params = {}) {
  const session = driver.session();
  try {
    const result = await session.run(cypher, params);
    return result.records.map(r => r.toObject());
  } finally {
    await session.close();
  }
}

// ── Get all stats for header ─────────────────────────────────
export async function getStats() {
  const rows = await runQuery(`
    MATCH (le:LoginEvent)
    RETURN
      COUNT(le) AS total_logins,
      SUM(CASE WHEN le.is_anomaly = true THEN 1 ELSE 0 END) AS anomalies
  `);
  const alerts = await runQuery(`
    MATCH (a:Alert) WHERE a.status = 'open' RETURN COUNT(a) AS open_alerts
  `);
  const servers = await runQuery(`
    MATCH (s:Server) RETURN COUNT(s) AS total_servers
  `);
  return {
    total_logins:   rows[0]?.total_logins?.toNumber()    || 0,
    anomalies:      rows[0]?.anomalies?.toNumber()       || 0,
    open_alerts:    alerts[0]?.open_alerts?.toNumber()   || 0,
    total_servers:  servers[0]?.total_servers?.toNumber()|| 0,
  };
}

// ── Get all nodes for graph ──────────────────────────────────
export async function getGraphNodes() {
  return await runQuery(`
    MATCH (n)
    WHERE n.id IS NOT NULL
    RETURN n.id AS id, labels(n)[0] AS type,
           n.name AS name, n.criticality AS criticality,
           n.status AS status
    LIMIT 60
  `);
}

// ── Get all edges for graph ──────────────────────────────────
export async function getGraphEdges() {
  return await runQuery(`
    MATCH (a)-[r]->(b)
    WHERE a.id IS NOT NULL AND b.id IS NOT NULL
    RETURN a.id AS source, b.id AS target, type(r) AS rel
    LIMIT 100
  `);
}

// ── Get CVE vulnerabilities ──────────────────────────────────
export async function getCVEs() {
  return await runQuery(`
    MATCH (s)-[v:HAS_VULNERABILITY]->(vuln:Vulnerability)
    RETURN s.name AS server_name,
           s.id   AS server_id,
           vuln.cve_id           AS cve_id,
           vuln.name             AS vuln_name,
           vuln.cvss_score       AS cvss_score,
           vuln.attack_vector    AS attack_vector,
           vuln.attack_complexity AS attack_complexity,
           vuln.exploit_available AS exploit_available
    ORDER BY vuln.cvss_score DESC
  `);
}

// ── Get anomalies ────────────────────────────────────────────
export async function getAnomalies() {
  return await runQuery(`
    MATCH (u:User)-[:PERFORMED]->(le:LoginEvent)-[:FROM_IP]->(ip:IPAddress)
    MATCH (le)-[:ACCESSED]->(s:Server)
    WHERE le.is_anomaly = true
    RETURN u.name          AS user,
           le.timestamp    AS time,
           le.risk_score   AS risk_score,
           le.failed_attempts AS attempts,
           ip.address      AS ip,
           ip.location     AS location,
           s.name          AS server,
           s.criticality   AS criticality
    ORDER BY le.risk_score DESC
    LIMIT 10
  `);
}

// ── Get alerts ───────────────────────────────────────────────
export async function getAlerts() {
  return await runQuery(`
    MATCH (a:Alert) WHERE a.status = 'open'
    RETURN a.id AS id, a.type AS type,
           a.severity AS severity, a.message AS message
    ORDER BY a.severity DESC
    LIMIT 10
  `);
}
