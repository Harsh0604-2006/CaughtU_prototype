import { useEffect, useState } from "react";

export default function RedAgentPanel({ attack, step }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (step >= 1 && attack) {
      setVisible(false);
      setTimeout(() => setVisible(true), 100);
    } else {
      setVisible(false);
    }
  }, [step, attack]);

  return (
    <div style={styles.wrapper}>
      <div style={styles.title}>
        <span style={styles.bar}/>
        RED AGENT — THREAT ANALYSIS
      </div>

      {!attack || step < 1 ? (
        <div style={styles.idle}>Awaiting attack simulation...</div>
      ) : (
        <div style={{ opacity: visible ? 1 : 0, transition:"opacity 0.5s" }}>
          <div style={styles.threatGrid}>
            <Row label="Entry Point" value={attack.entry}    color="var(--red)"    />
            <Row label="Via CVE"     value={attack.cve}      color="var(--red)"    />
            <Row label="Vuln Name"   value={attack.name}     color="var(--text)"   />
            <Row label="Source IP"   value={attack.ip}       color="var(--red)"    />
            <Row label="Location"    value={attack.location} color="var(--red)"    />
            <Row label="Time"        value={attack.hour}     color="var(--text)"   />
            <Row label="Attempts"    value={`${attack.attempts} failed`} color="var(--red)" />
            <Row label="Risk Score"  value={`${attack.risk}/100`}        color="var(--red)" />
          </div>

          {/* Attack path */}
          <div style={styles.pathSection}>
            <div style={styles.pathLabel}>ATTACK PATH</div>
            <div style={styles.pathRow}>
              {attack.path.map((node, i) => (
                <span key={i} style={{ display:"flex", alignItems:"center", gap:4 }}>
                  <span style={styles.pathNode}>{node}</span>
                  {i < attack.path.length - 1 && (
                    <span style={{ color:"var(--dim)" }}>→</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          {/* Risk banner */}
          <div style={styles.riskBanner}>
            ⚠ NODES AT RISK: {attack.path.length} — IMMEDIATE ACTION REQUIRED
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, color }) {
  return (
    <div style={{ display:"contents" }}>
      <div style={{ fontFamily:"'Share Tech Mono',monospace", fontSize:11, color:"var(--dim)", padding:"3px 0" }}>
        {label}
      </div>
      <div style={{ fontFamily:"'Share Tech Mono',monospace", fontSize:11, color, padding:"3px 0" }}>
        {value}
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    background:"var(--panel)",
    padding:"16px",
    borderLeft:"2px solid var(--red)",
    overflow:"auto",
  },
  title: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, letterSpacing:3,
    textTransform:"uppercase",
    color:"var(--dim)",
    marginBottom:12,
    display:"flex", alignItems:"center", gap:8,
  },
  bar: {
    display:"inline-block",
    width:3, height:12,
    background:"var(--red)",
  },
  idle: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:12, color:"var(--dim)",
  },
  threatGrid: {
    display:"grid",
    gridTemplateColumns:"auto 1fr",
    gap:"0 16px",
    marginBottom:12,
  },
  pathSection: { marginBottom:12 },
  pathLabel: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:10, color:"var(--dim)",
    letterSpacing:2, marginBottom:6,
  },
  pathRow: {
    display:"flex", flexWrap:"wrap", gap:4,
    fontFamily:"'Share Tech Mono',monospace",
  },
  pathNode: {
    color:"var(--text)", fontSize:11,
    padding:"2px 6px",
    border:"1px solid var(--border)",
    borderRadius:2,
  },
  riskBanner: {
    padding:"8px 12px",
    border:"1px solid rgba(255,45,85,0.3)",
    background:"rgba(255,45,85,0.06)",
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, color:"var(--red)",
  },
};
