// ── api.js — Backend API Client ───────────────────────────────
// Connects to the live FastAPI backend on localhost:8000

const BASE_URL = "http://localhost:8000";

// Helper to handle API responses
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    throw error;
  }
}

// ── Red Agent API ─────────────────────────────────────────────

/**
 * Trigger Red Agent attack vector analysis
 * @param {string} graph - 'prod' or 'sim'
 * @param {string} focusServer - optional specific server to target
 */
export async function analyzeAttackVectors(graph = "prod", focusServer = null) {
  return fetchAPI("/api/red-agent/analyze", {
    method: "POST",
    body: JSON.stringify({ graph, focus_server: focusServer })
  });
}

/**
 * Get all servers
 */
export async function getServers(graph = "prod") {
  return fetchAPI(`/api/red-agent/servers/${graph}`);
}

/**
 * Get all vulnerabilities
 */
export async function getVulnerabilities(graph = "prod") {
  return fetchAPI(`/api/red-agent/vulnerabilities/${graph}`);
}

/**
 * Get system stats for header
 * The backend doesn't have a direct /stats endpoint matching the mock, 
 * so we simulate it or fetch relevant counts (like total servers).
 */
export async function getStats(graph = "prod") {
  try {
    const serversData = await getServers(graph);
    return {
      total_servers: serversData.servers_count || 0,
      open_alerts: 0,
      anomalies: 0,
      total_logins: 0,
    };
  } catch (err) {
    return {
      total_servers: 0, open_alerts: 0, anomalies: 0, total_logins: 0
    };
  }
}

// ── Blue Agent API ────────────────────────────────────────────

/**
 * Generate remediation playbook
 */
export async function generatePlaybook(attackVector, serverProperties, riskContext = null) {
  return fetchAPI("/api/blue-agent/remediation-playbook", {
    method: "POST",
    body: JSON.stringify({
      attack_vector: attackVector,
      server_properties: serverProperties,
      risk_context: riskContext
    })
  });
}

/**
 * Apply isolation fix
 */
export async function isolateServer(graph, serverName) {
  return fetchAPI(`/api/blue-agent/isolate/${graph}/${serverName}`, {
    method: "POST"
  });
}
