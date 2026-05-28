import { useEffect, useState } from "react";

export default function Header({ stats, statusText, onSimulate }) {
  const [blink, setBlink] = useState(true);

  useEffect(() => {
    const t = setInterval(() => setBlink(b => !b), 800);
    return () => clearInterval(t);
  }, []);

  const isAttack   = statusText === "UNDER ATTACK";
  const isSecured  = statusText === "SECURED";
  const statusColor = isAttack ? "var(--red)" : isSecured ? "var(--green)" : "var(--accent)";

  return (
    <div style={styles.header}>
      {/* Logo */}
      <div style={styles.logo}>
        <div style={{
          ...styles.logoDot,
          background: isAttack ? "var(--red)" : "var(--accent)",
          boxShadow: `0 0 14px ${isAttack ? "var(--red)" : "var(--accent)"}`,
          opacity: blink ? 1 : 0.4,
        }}/>
        <span style={styles.logoText}>
          CAUGHT <span style={{ color:"var(--red)" }}>U!</span>
        </span>
        <span style={styles.logoSub}>AI CYBERSECURITY · PSBs 2026</span>
      </div>

      {/* Stats */}
      <div style={styles.statsRow}>
        <Stat label="LOGINS"    value={stats.total_logins}  color="var(--accent)" />
        <Stat label="ANOMALIES" value={stats.anomalies}     color={stats.anomalies > 0 ? "var(--red)" : "var(--text)"} />
        <Stat label="ALERTS"    value={stats.open_alerts}   color={stats.open_alerts > 0 ? "var(--red)" : "var(--text)"} />
        <Stat label="SERVERS"   value={stats.total_servers} color="var(--green)" />
      </div>

      {/* Status + button */}
      <div style={styles.right}>
        <div style={{ ...styles.statusPill, borderColor: statusColor, color: statusColor }}>
          <div style={{ ...styles.statusDot, background: statusColor, opacity: blink ? 1 : 0.3 }}/>
          {statusText}
        </div>
        <button style={styles.simBtn} onClick={onSimulate}>
          ⚡ SIMULATE ATTACK
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign:"center" }}>
      <div style={{ fontFamily:"'Orbitron',monospace", fontSize:18, fontWeight:700, color }}>
        {value}
      </div>
      <div style={{ fontFamily:"'Share Tech Mono',monospace", fontSize:9, color:"var(--dim)", letterSpacing:1, textTransform:"uppercase" }}>
        {label}
      </div>
    </div>
  );
}

const styles = {
  header: {
    display:"flex", alignItems:"center", justifyContent:"space-between",
    padding:"10px 20px",
    background:"var(--panel)",
    borderBottom:"1px solid var(--border)",
    zIndex:10,
    flexShrink:0,
  },
  logo: { display:"flex", alignItems:"center", gap:12 },
  logoDot: {
    width:12, height:12, borderRadius:"50%",
    transition:"all 0.3s",
  },
  logoText: {
    fontFamily:"'Orbitron',monospace",
    fontSize:20, fontWeight:900,
    color:"#fff", letterSpacing:4,
  },
  logoSub: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:10, color:"var(--dim)",
    letterSpacing:2, marginLeft:8,
  },
  statsRow: { display:"flex", gap:24 },
  right: { display:"flex", alignItems:"center", gap:16 },
  statusPill: {
    display:"flex", alignItems:"center", gap:8,
    padding:"4px 14px",
    border:"1px solid",
    borderRadius:2,
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, letterSpacing:2,
    transition:"all 0.3s",
  },
  statusDot: {
    width:6, height:6, borderRadius:"50%",
    transition:"opacity 0.3s",
  },
  simBtn: {
    padding:"8px 20px",
    background:"transparent",
    border:"1px solid var(--red)",
    color:"var(--red)",
    fontFamily:"'Orbitron',monospace",
    fontSize:11, fontWeight:700,
    letterSpacing:2, cursor:"pointer",
    transition:"all 0.3s",
  },
};
