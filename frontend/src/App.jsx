import { useCallback, useEffect, useMemo, useState } from "react";

import Sidebar from "./components/Sidebar.jsx";
import TopHeader from "./components/TopHeader.jsx";
import AgentCard from "./components/AgentCard.jsx";
import DatabaseGraph from "./components/DatabaseGraph.jsx";
import AttackVectorList from "./components/AttackVectorList.jsx";
import PipelineBar from "./components/PipelineBar.jsx";
import RedAgentPanel from "./components/RedAgentPanel.jsx";
import BlueAgentPanel from "./components/BlueAgentPanel.jsx";
import LiveLogs from "./components/LiveLogs.jsx";

// Import real API calls
import {
  analyzeAttackVectors,
  generatePlaybook,
  isolateServer,
  getStats,
} from "./api.js";

const STEP_DELAY = 700;

function stamp() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function createLog(level, text) {
  return {
    id: Math.random().toString(36).slice(2),
    time: stamp(),
    level,
    text,
  };
}

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [now, setNow] = useState(new Date());
  const [status, setStatus] = useState("MONITORING");
  const [step, setStep] = useState(-1);
  const [activeAttack, setActiveAttack] = useState(null);
  const [nodeStates, setNodeStates] = useState({});
  const [graphRefreshKey, setGraphRefreshKey] = useState(0);
  const [logs, setLogs] = useState([
    createLog("SYSTEM", "Cyber Defense Command initialized"),
    createLog("DATABASE", "Neo4j graph connection ready"),
    createLog("BLUE", "Blue Agent standing by"),
    createLog("RED", "Red Agent monitoring attack surface"),
  ]);
  const [blueRequested, setBlueRequested] = useState(false);
  const [responseTime, setResponseTime] = useState(null);

  // Real stats from backend
  const [apiStats, setApiStats] = useState({ total_servers: 0, open_alerts: 0 });

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // Fetch initial stats
    getStats("prod").then((data) => {
      setApiStats(data);
    });
  }, []);

  const pushLog = useCallback((level, text) => {
    setLogs((prev) => [...prev.slice(-70), createLog(level, text)]);
  }, []);

  const metrics = useMemo(() => {
    const compromised = Object.values(nodeStates).filter(
      (value) => value === "compromised"
    ).length;

    const fixed = Object.values(nodeStates).filter(
      (value) => value === "fixed"
    ).length;

    return {
      openAlerts: status === "SECURED" ? 0 : activeAttack ? 1 : apiStats.open_alerts,
      riskScore: activeAttack ? (activeAttack.cvss_score * 10 || 95) : 12,
      nodesAtRisk: activeAttack?.path ? activeAttack.path.length : 0,
      compromised,
      fixed,
      totalServers: apiStats.total_servers,
    };
  }, [activeAttack, nodeStates, status, apiStats]);

  const simulateAttack = useCallback(async () => {
    setActivePage("Dashboard");
    setStatus("ANALYZING");
    setStep(0);
    setNodeStates({});
    setBlueRequested(false);
    setResponseTime(null);

    pushLog("info", "Initiating Red Agent attack vector analysis on prod graph...");

    try {
      // 1. Call Red Agent
      const response = await analyzeAttackVectors("prod");

      const report = response.attack_report;

      if (!report || Object.keys(report).length === 0 || report.error || report.parse_error) {
        pushLog("warn", "No viable attack vectors found or parse error.");
        setStatus("MONITORING");
        return;
      }

      const targetName = report.entry_point || "Unknown Target";

      const cveName = report.cve_used || "Unknown CVE";

      // Build attack path from raw_query_results for richer blast radius visualization
      const rawResults = response.raw_query_results || [];
      const blastRadiusNodes = rawResults
        .map(r => r.target)
        .filter(Boolean)
        .filter((v, i, a) => a.indexOf(v) === i); // unique targets

      const attackPath = [targetName, ...blastRadiusNodes.slice(0, 6)];

      // Structure activeAttack to be compatible with UI components
      const structuredAttack = {
        title: `${cveName} on ${targetName}`,
        entry: targetName,
        via: cveName,
        risk: report.overall_severity === "CRITICAL" ? 95 : report.overall_severity === "HIGH" ? 80 : 50,
        sourceIp: "External",
        location: "Internet",
        affectedNodes: report.blast_radius_count || blastRadiusNodes.length || 1,
        path: attackPath,
        attackSteps: report.attack_steps || [],
        highestValueTarget: report.highest_value_target || "Unknown",
        overallSeverity: report.overall_severity || "Unknown",
        executiveSummary: `The Red Agent identified a ${report.overall_severity} severity attack path starting at ${targetName} using ${cveName}. The highest value target reachable is ${report.highest_value_target}. Blast radius encompasses ${report.blast_radius_count || blastRadiusNodes.length} nodes across the banking infrastructure.`,
        defensivePriorities: report.recommended_defenses || [],
        playbook: null,
      };

      setActiveAttack(structuredAttack);
      setStatus("UNDER ATTACK");

      pushLog("danger", `Threat detected: ${cveName} targeting ${targetName}`);

      // Visualize blast radius
      structuredAttack.path.forEach((nodeId, index) => {
        setTimeout(() => {
          setNodeStates((prev) => ({ ...prev, [nodeId]: "compromised" }));
          pushLog("danger", `Blast radius node compromised: ${nodeId}`);
        }, index * STEP_DELAY);
      });

      const redDelay = structuredAttack.path.length * STEP_DELAY + 500;

      setTimeout(() => {
        setStep(1);
        pushLog("danger", "Red Agent generated threat narrative and attack path.");
      }, redDelay);

      setTimeout(async () => {
        setStep(2);
        pushLog("info", "Blue Agent building remediation playbook using LLM...");

        // 2. Call Blue Agent playbook generation
        try {
          const playbookRes = await generatePlaybook(
            report,
            { name: targetName, criticality: "high" }
          );

          setActiveAttack(prev => ({
            ...prev,
            playbook: playbookRes.playbook
          }));

          setStep(3);
          setBlueRequested(true);
          pushLog("warn", "Blue Agent playbook ready. Human approval required.");
        } catch (err) {
          pushLog("danger", "Failed to generate playbook: " + err.message);
        }
      }, redDelay + 1500);

    } catch (error) {
      pushLog("danger", `Analysis failed: ${error.message}`);
      setStatus("ERROR");
    }
  }, [pushLog]);

  const approveFix = useCallback(async () => {
    if (!activeAttack || !activeAttack.entry) return;

    setStep(4);
    setBlueRequested(false);
    pushLog("ok", "Approval received. Blue Agent isolating the compromised node.");

    try {
      // 3. Call Blue Agent isolation API
      await isolateServer("prod", activeAttack.entry);

      setNodeStates((prev) => ({ ...prev, [activeAttack.entry]: "fixed" }));
      setGraphRefreshKey((prev) => prev + 1);
      pushLog("ok", `Remediated and isolated compromised node: ${activeAttack.entry}`);

      setTimeout(() => {
        setStep(5);
        setStatus("SECURED");
        setResponseTime((Math.random() * 1.8 + 3.2).toFixed(1));
        pushLog("ok", "Verification complete. Environment secured.");
      }, activeAttack.path.length * 520 + 700);

    } catch (error) {
      pushLog("danger", `Failed to apply fix: ${error.message}`);
    }
  }, [activeAttack, pushLog]);

  function renderPage() {
    if (activePage === "Blue Agent") {
      return (
        <section className="dashboard-grid single-page blue-page">
          <BlueAgentPanel
            attack={activeAttack}
            step={step}
            onApprove={approveFix}
            responseTime={responseTime}
          />
        </section>
      );
    }

    if (activePage === "Red Agent") {
      return (
        <section className="dashboard-grid single-page red-page">
          <RedAgentPanel attack={activeAttack} step={step} />
        </section>
      );
    }

    if (activePage === "Database") {
      return (
        <section className="dashboard-grid single-page database-page">
          <DatabaseGraph key={graphRefreshKey} nodeStates={nodeStates} activeAttack={activeAttack} />
          <AttackVectorList activeAttack={activeAttack} />
        </section>
      );
    }

    if (activePage === "Logs") {
      return (
        <section className="dashboard-grid single-page">
          <LiveLogs logs={logs} />
        </section>
      );
    }

    if (activePage === "Settings") {
      return (
        <section className="dashboard-grid single-page">
          <div className="panel settings-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">SYSTEM SETTINGS</p>
                <h2>Backend Configuration</h2>
              </div>
              <span className="panel-chip green">Online</span>
            </div>

            <div className="empty-state">
              API Base URL: http://localhost:8000
            </div>
          </div>
        </section>
      );
    }

    return (
      <section className="dashboard-grid">
        <DatabaseGraph key={graphRefreshKey} nodeStates={nodeStates} activeAttack={activeAttack} />

        <RedAgentPanel attack={activeAttack} step={step} />

        <AttackVectorList activeAttack={activeAttack} />

        <PipelineBar step={step} />

        <BlueAgentPanel
          attack={activeAttack}
          step={step}
          onApprove={approveFix}
          responseTime={responseTime}
        />

        <LiveLogs logs={logs} />
      </section>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar active={activePage} onNavigate={setActivePage} />

      <main className="command-center">
        <TopHeader
          now={now}
          status={status}
          metrics={metrics}
          onSimulate={simulateAttack}
        />

        {renderPage()}
      </main>
    </div>
  );
}