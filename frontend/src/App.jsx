import { useState, useEffect, useCallback } from "react";
import Header           from "./components/Header";
import GraphPanel       from "./components/GraphPanel";
import AttackVectorList from "./components/AttackVectorList";
import StateBar         from "./components/StateBar";
import RedAgentPanel    from "./components/RedAgentPanel";
import PlaybookPanel    from "./components/PlaybookPanel";
import { getStats, getAnomalies, getAlerts } from "./api";

// ── Attack scenarios (3 random attacks) ─────────────────────
const ATTACKS = [
  {
    cve: "CVE-2021-44228", name: "Log4Shell",
    entry: "SRV002", server: "CoreDBServer01",
    ip: "45.33.12.156", location: "Russia",
    hour: "03:22 AM", attempts: 8, risk: 90,
    path: ["SRV002","SRV001","API003","BANK001","SRV007"],
    playbook: [
      { icon:"🔒", text:"Isolate CoreDBServer01 from internal zone" },
      { icon:"🔑", text:"Force password reset — all active sessions" },
      { icon:"🛡️", text:"Block ports 389 and 636 at Firewall01" },
      { icon:"🔧", text:"Apply patch for CVE-2021-44228 (Log4j 2.17.1)" },
      { icon:"✅", text:"Verify no active sessions from 45.33.12.156" },
    ],
  },
  {
    cve: "CVE-2022-22965", name: "Spring4Shell",
    entry: "NET006", server: "AppServer01",
    ip: "103.21.58.99", location: "China",
    hour: "02:15 AM", attempts: 12, risk: 95,
    path: ["NET006","SRV006","SRV002","SRV001","BANK001"],
    playbook: [
      { icon:"🔒", text:"Isolate AppServer01 immediately" },
      { icon:"🚫", text:"Block IP range 103.21.0.0/16 at gateway" },
      { icon:"🔧", text:"Apply Spring Framework patch 5.3.18+" },
      { icon:"🔑", text:"Rotate all API keys and session tokens" },
      { icon:"✅", text:"Scan all Java apps for vulnerable Spring versions" },
    ],
  },
  {
    cve: "CVE-2023-34362", name: "MOVEit SQL Injection",
    entry: "SRV004", server: "BackupServer01",
    ip: "185.220.101.5", location: "Germany",
    hour: "04:00 AM", attempts: 5, risk: 80,
    path: ["SRV004","SRV001","API001","BANK001"],
    playbook: [
      { icon:"🔒", text:"Take BackupServer01 offline immediately" },
      { icon:"🗄️", text:"Audit all database access logs for SQL anomalies" },
      { icon:"🔧", text:"Apply MOVEit Transfer security patch" },
      { icon:"🛡️", text:"Enable WAF rules for SQL injection patterns" },
      { icon:"✅", text:"Verify database integrity — check for exfiltration" },
    ],
  },
];

export default function App() {
  // ── global state ─────────────────────────────────────────
  const [step,            setStep]            = useState(-1);
  const [attack,          setAttack]          = useState(null);
  const [nodeStates,      setNodeStates]      = useState({});
  const [stats,           setStats]           = useState({ total_logins:0, anomalies:0, open_alerts:0, total_servers:0 });
  const [statusText,      setStatusText]      = useState("MONITORING");
  const [complianceDone,  setComplianceDone]  = useState(false);
  const [responseTime,    setResponseTime]    = useState(null);

  // load live stats on mount
  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  // ── simulate attack ──────────────────────────────────────
  const simulateAttack = useCallback(() => {
    const a = ATTACKS[Math.floor(Math.random() * ATTACKS.length)];
    setAttack(a);
    setStep(0);
    setNodeStates({});
    setStatusText("UNDER ATTACK");
    setComplianceDone(false);
    setResponseTime(null);
    setStats(s => ({ ...s, anomalies: Math.floor(Math.random()*8)+3, open_alerts: Math.floor(Math.random()*5)+2 }));

    // blast radius — light nodes red one by one
    a.path.forEach((id, i) => {
      setTimeout(() => {
        setNodeStates(prev => ({ ...prev, [id]: "compromised" }));
        if (i === a.path.length - 1) {
          setTimeout(() => setStep(1), 600);
        }
      }, i * 400);
    });
  }, []);

  // auto-advance step 1 → 2
  useEffect(() => {
    if (step === 1) {
      const t = setTimeout(() => setStep(2), 1800);
      return () => clearTimeout(t);
    }
  }, [step]);

  // auto-advance step 2 → 3 after playbook loads
  useEffect(() => {
    if (step === 2) {
      const t = setTimeout(() => setStep(3), attack?.playbook.length * 350 + 800 || 2500);
      return () => clearTimeout(t);
    }
  }, [step, attack]);

  // ── approve and apply fix ────────────────────────────────
  const approveAndApply = useCallback(() => {
    if (!attack) return;
    setStep(4);

    attack.path.forEach((id, i) => {
      setTimeout(() => {
        setNodeStates(prev => ({ ...prev, [id]: "fixed" }));
        if (i === attack.path.length - 1) {
          setTimeout(() => {
            setStep(5);
            setStatusText("SECURED");
            setStats(s => ({ ...s, open_alerts: 0 }));
            setComplianceDone(true);
            setResponseTime((Math.random()*2+3).toFixed(1));
          }, 600);
        }
      }, i * 350);
    });
  }, [attack]);

  return (
    <div style={styles.root}>
      <Header
        stats={stats}
        statusText={statusText}
        onSimulate={simulateAttack}
      />
      <div style={styles.main}>
        {/* Left: graph */}
        <GraphPanel nodeStates={nodeStates} />

        {/* Right: CVEs + compliance */}
        <AttackVectorList
          complianceDone={complianceDone}
          responseTime={responseTime}
        />

        {/* Pipeline bar */}
        <StateBar step={step} />

        {/* Bottom two panels */}
        <div style={styles.bottomGrid}>
          <RedAgentPanel attack={attack} step={step} />
          <PlaybookPanel
            attack={attack}
            step={step}
            onApprove={approveAndApply}
          />
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    background: "var(--bg)",
  },
  main: {
    flex: 1,
    display: "grid",
    gridTemplateColumns: "1fr 340px",
    gridTemplateRows: "1fr auto 260px",
    gap: "1px",
    background: "var(--border)",
    overflow: "hidden",
  },
  bottomGrid: {
    gridColumn: "1 / -1",
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "1px",
    background: "var(--border)",
  },
};
