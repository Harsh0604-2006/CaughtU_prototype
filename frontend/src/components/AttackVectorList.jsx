import { useEffect, useState } from "react";

const CVE_DATA = [
  { cve:"CVE-2021-44228", name:"Log4Shell — Apache Log4j2 RCE",      score:10.0, server:"CoreDBServer01", priority:"P1", sev:"critical" },
  { cve:"CVE-2022-22965", name:"Spring4Shell — RCE via Data Binding", score:9.8,  server:"AppServer01",   priority:"P1", sev:"critical" },
  { cve:"CVE-2023-34362", name:"MOVEit SQL Injection",                score:9.8,  server:"BackupServer01",priority:"P1", sev:"critical" },
  { cve:"CVE-2023-44487", name:"HTTP/2 Rapid Reset DDoS",             score:7.5,  server:"LoadBalancer01",priority:"P2", sev:"high"     },
];

const COMPLIANCE = ["RBI", "BASEL III", "ISO 27001", "PCI DSS"];

export default function AttackVectorList({ complianceDone, responseTime }) {
  const [passedBadges, setPassedBadges] = useState([]);

  useEffect(() => {
    if (complianceDone) {
      COMPLIANCE.forEach((_, i) => {
        setTimeout(() => {
          setPassedBadges(prev => [...prev, i]);
        }, i * 450);
      });
    } else {
      setPassedBadges([]);
    }
  }, [complianceDone]);

  const scoreColor = (s) => {
    if (s >= 10) return "var(--red)";
    if (s >= 9)  return "var(--red)";
    if (s >= 7)  return "var(--orange)";
    return "var(--yellow)";
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.title}>
        <span style={styles.bar}/>
        ATTACK VECTORS — CVE DATABASE
      </div>

      {/* CVE list */}
      <div style={{ flex:1, overflowY:"auto" }}>
        {CVE_DATA.map((item, i) => (
          <div key={i} style={{
            ...styles.cveItem,
            borderLeft:`3px solid ${item.sev === "critical" ? "var(--red)" : "var(--orange)"}`,
          }}>
            <div style={styles.cveTop}>
              <span style={styles.cveId}>{item.cve}</span>
              <span style={{ fontFamily:"'Orbitron',monospace", fontSize:15, fontWeight:700, color: scoreColor(item.score) }}>
                {item.score}
              </span>
            </div>
            <div style={styles.cveName}>{item.name}</div>
            <div style={styles.cveBottom}>
              <span style={styles.cveServer}>{item.server}</span>
              <span style={{
                ...styles.badge,
                color: item.sev === "critical" ? "var(--red)" : "var(--orange)",
                border: `1px solid ${item.sev === "critical" ? "var(--red)" : "var(--orange)"}`,
                background: item.sev === "critical" ? "rgba(255,45,85,0.1)" : "rgba(255,107,43,0.1)",
              }}>
                {item.priority} {item.sev.toUpperCase()}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Compliance */}
      <div style={styles.compSection}>
        <div style={{ ...styles.title, marginBottom:8 }}>
          <span style={styles.bar}/>
          COMPLIANCE STATUS
        </div>
        <div style={styles.badgeRow}>
          {COMPLIANCE.map((name, i) => (
            <div key={i} style={{
              ...styles.compBadge,
              borderColor:    passedBadges.includes(i) ? "var(--green)" : "var(--border)",
              color:          passedBadges.includes(i) ? "var(--green)" : "var(--dim)",
              background:     passedBadges.includes(i) ? "rgba(0,255,157,0.08)" : "transparent",
              boxShadow:      passedBadges.includes(i) ? "0 0 8px rgba(0,255,157,0.2)" : "none",
              transition:     "all 0.5s",
            }}>
              {passedBadges.includes(i) ? "✓ " : ""}{name}
            </div>
          ))}
        </div>
        {responseTime && (
          <div style={styles.respTime}>
            ⚡ TOTAL RESPONSE TIME: {responseTime}s
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    background:"var(--panel)",
    padding:"16px",
    gridRow:1, gridColumn:2,
    display:"flex", flexDirection:"column",
    overflow:"hidden",
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
    background:"var(--accent)",
  },
  cveItem: {
    padding:"10px 12px",
    border:"1px solid var(--border)",
    marginBottom:8,
    borderRadius:2,
    cursor:"pointer",
    transition:"border-color 0.2s",
  },
  cveTop: {
    display:"flex", justifyContent:"space-between", alignItems:"center",
    marginBottom:4,
  },
  cveId: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:12, color:"var(--accent)",
  },
  cveName: {
    fontSize:12, color:"var(--text)", marginBottom:4,
  },
  cveBottom: {
    display:"flex", justifyContent:"space-between", alignItems:"center",
  },
  cveServer: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:10, color:"var(--dim)",
  },
  badge: {
    fontSize:9, fontWeight:700,
    padding:"2px 6px", borderRadius:2, letterSpacing:1,
  },
  compSection: {
    marginTop:"auto",
    paddingTop:12,
    borderTop:"1px solid var(--border)",
  },
  badgeRow: {
    display:"flex", gap:6, flexWrap:"wrap",
  },
  compBadge: {
    padding:"4px 10px",
    borderRadius:2, border:"1px solid",
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:10, letterSpacing:1,
  },
  respTime: {
    fontFamily:"'Orbitron',monospace",
    fontSize:11, color:"var(--green)",
    marginTop:8,
  },
};
