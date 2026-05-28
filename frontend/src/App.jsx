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

import { attacks, initialLogs } from "./data/mockData.js";

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
  const [logs, setLogs] = useState(() =>
    initialLogs.map((log) =>
      createLog(
        log.level || log.type || "info",
        log.text || log.message || "System event detected"
      )
    )
  );
  const [blueRequested, setBlueRequested] = useState(false);
  const [responseTime, setResponseTime] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
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
      openAlerts: status === "SECURED" ? 0 : activeAttack ? 3 : 0,
      riskScore: activeAttack ? activeAttack.risk : 12,
      nodesAtRisk: activeAttack ? activeAttack.path.length : 0,
      compromised,
      fixed,
    };
  }, [activeAttack, nodeStates, status]);

  const simulateAttack = useCallback(() => {
    const chosen = attacks[Math.floor(Math.random() * attacks.length)];

    setActivePage("Dashboard");
    setActiveAttack(chosen);
    setStatus("UNDER ATTACK");
    setStep(0);
    setNodeStates({});
    setBlueRequested(false);
    setResponseTime(null);

    const cveName = chosen.cve || chosen.via || "Unknown CVE";
    const targetName = chosen.target || chosen.entry || "Unknown target";

    setLogs((prev) => [
      ...prev.slice(-40),
      createLog(
        "danger",
        `Simulated breach started: ${cveName} targeting ${targetName}.`
      ),
      createLog(
        "info",
        "Blast radius scan started. Lighting affected database graph nodes."
      ),
    ]);

    chosen.path.forEach((nodeId, index) => {
      setTimeout(() => {
        setNodeStates((prev) => ({ ...prev, [nodeId]: "compromised" }));
        pushLog("danger", `Blast radius node marked: ${nodeId}`);
      }, index * STEP_DELAY);
    });

    const redDelay = chosen.path.length * STEP_DELAY + 500;

    setTimeout(() => {
      setStep(1);
      pushLog("danger", "Red Agent generated threat narrative and attack path.");
    }, redDelay);

    setTimeout(() => {
      setStep(2);
      pushLog("info", "Blue Agent building remediation playbook.");
    }, redDelay + 1500);

    setTimeout(() => {
      setStep(3);
      setBlueRequested(true);
      pushLog("warn", "Blue Agent requests human approval before applying fix.");
    }, redDelay + 3500);
  }, [pushLog]);

  const approveFix = useCallback(() => {
    if (!activeAttack) return;

    setStep(4);
    setBlueRequested(false);
    pushLog("ok", "Approval received. Blue Agent applying remediation sequence.");

    activeAttack.path.forEach((nodeId, index) => {
      setTimeout(() => {
        setNodeStates((prev) => ({ ...prev, [nodeId]: "fixed" }));
        pushLog("ok", `Remediated node: ${nodeId}`);
      }, index * 520);
    });

    setTimeout(() => {
      setStep(5);
      setStatus("SECURED");
      setResponseTime((Math.random() * 1.8 + 3.2).toFixed(1));
      pushLog(
        "ok",
        "Verification complete. Environment secured and monitoring resumed."
      );
    }, activeAttack.path.length * 520 + 700);
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
        <section className="dashboard-grid single-page">
          <DatabaseGraph nodeStates={nodeStates} activeAttack={activeAttack} />
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
                <h2>Command Configuration</h2>
              </div>
              <span className="panel-chip green">Online</span>
            </div>

            <div className="empty-state">
              Settings module placeholder. Add backend configuration here.
            </div>
          </div>
        </section>
      );
    }

    return (
      <section className="dashboard-grid">
        <div className="agent-row">
          <AgentCard
            type="blue"
            title="Blue Agent"
            subtitle="Defense Automation"
            status={
              blueRequested
                ? "Approval Required"
                : status === "SECURED"
                ? "Verified Clean"
                : "Standing By"
            }
            metricLabel="Playbook Confidence"
            metricValue={activeAttack ? "96%" : "Ready"}
            description="Builds containment, patching and verification playbooks before requesting approval."
          />

          <AgentCard
            type="red"
            title="Red Agent"
            subtitle="Threat Simulation"
            status={activeAttack ? "Attack Path Found" : "Idle"}
            metricLabel="Current Risk"
            metricValue={activeAttack ? `${activeAttack.risk}/100` : "12/100"}
            description="Maps entry point, CVE route, blast radius and possible lateral movement."
          />
        </div>

        <DatabaseGraph nodeStates={nodeStates} activeAttack={activeAttack} />

        <AttackVectorList activeAttack={activeAttack} />

        <PipelineBar step={step} />

        <RedAgentPanel attack={activeAttack} step={step} />

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