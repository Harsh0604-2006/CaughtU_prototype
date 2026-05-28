import { useEffect, useState } from "react";

export default function PlaybookPanel({ attack, step, onApprove }) {
  const [visibleSteps, setVisibleSteps] = useState([]);
  const [approved, setApproved]         = useState(false);

  useEffect(() => {
    if (step >= 2 && attack) {
      setVisibleSteps([]);
      setApproved(false);
      attack.playbook.forEach((_, i) => {
        setTimeout(() => {
          setVisibleSteps(prev => [...prev, i]);
        }, i * 320);
      });
    }
    if (step < 2) {
      setVisibleSteps([]);
      setApproved(false);
    }
  }, [step, attack]);

  const handleApprove = () => {
    if (approved) return;
    setApproved(true);
    onApprove();
  };

  const showApprove = step >= 3;
  const btnDone = step >= 4;

  return (
    <div style={styles.wrapper}>
      <div style={styles.title}>
        <span style={styles.bar}/>
        BLUE AGENT — REMEDIATION PLAYBOOK
      </div>

      {!attack || step < 2 ? (
        <div style={styles.idle}>Awaiting threat detection...</div>
      ) : (
        <>
          <div style={styles.steps}>
            {attack.playbook.map((s, i) => (
              <div key={i} style={{
                ...styles.pbStep,
                opacity:   visibleSteps.includes(i) ? 1 : 0,
                transform: visibleSteps.includes(i) ? "translateX(0)" : "translateX(-12px)",
                transition:`opacity 0.4s, transform 0.4s`,
              }}>
                <div style={styles.pbNum}>0{i+1}</div>
                <div style={styles.pbIcon}>{s.icon}</div>
                <div style={styles.pbText}>{s.text}</div>
              </div>
            ))}
          </div>

          {showApprove && (
            <button
              style={{
                ...styles.approveBtn,
                borderColor: btnDone ? "var(--green)" : "var(--red)",
                color:       btnDone ? "var(--green)" : "var(--red)",
                background:  btnDone ? "rgba(0,255,157,0.06)" : "transparent",
                cursor: approved ? "default" : "pointer",
              }}
              onClick={handleApprove}
            >
              {btnDone
                ? "✅ FIX APPROVED & APPLIED"
                : "⚡ APPROVE & APPLY FIX"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    background:"var(--panel)",
    padding:"16px",
    borderLeft:"2px solid var(--accent)",
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
    flexShrink:0,
  },
  bar: {
    display:"inline-block",
    width:3, height:12,
    background:"var(--accent)",
  },
  idle: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:12, color:"var(--dim)",
  },
  steps: {
    flex:1,
    overflowY:"auto",
  },
  pbStep: {
    display:"flex", alignItems:"flex-start", gap:10,
    padding:"8px 0",
    borderBottom:"1px solid var(--border)",
  },
  pbNum: {
    fontFamily:"'Orbitron',monospace",
    fontSize:11, fontWeight:700,
    color:"var(--accent)",
    minWidth:20, marginTop:1,
  },
  pbIcon: { fontSize:14, minWidth:20 },
  pbText: {
    fontSize:13, color:"var(--text)", lineHeight:1.4,
  },
  approveBtn: {
    width:"100%",
    padding:"12px",
    marginTop:10,
    border:"1px solid",
    borderRadius:2,
    fontFamily:"'Orbitron',monospace",
    fontSize:11, fontWeight:700,
    letterSpacing:2,
    textTransform:"uppercase",
    transition:"all 0.3s",
    flexShrink:0,
  },
};
