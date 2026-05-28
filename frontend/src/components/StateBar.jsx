const STEPS = [
  { icon:"🔍", label:"BLAST RADIUS" },
  { icon:"🔴", label:"RED REPORT"   },
  { icon:"📋", label:"PLAYBOOK"     },
  { icon:"⏸",  label:"APPROVE"     },
  { icon:"🛡️", label:"FIX APPLIED" },
  { icon:"✅", label:"VERIFIED"    },
];

export default function StateBar({ step }) {
  return (
    <div style={styles.bar}>
      {STEPS.map((s, i) => {
        let state = "idle";
        if (i < step)  state = "done";
        if (i === step) state = "active";
        if (i === 3 && step === 3) state = "danger";

        return (
          <div key={i} style={{ display:"flex", alignItems:"center" }}>
            <div style={{
              ...styles.step,
              borderColor:   state === "done"   ? "var(--green)"  :
                             state === "active" ? "var(--accent)" :
                             state === "danger" ? "var(--red)"    : "var(--border)",
              color:         state === "done"   ? "var(--green)"  :
                             state === "active" ? "var(--accent)" :
                             state === "danger" ? "var(--red)"    : "var(--dim)",
              background:    state === "done"   ? "rgba(0,255,157,0.05)"  :
                             state === "active" ? "rgba(0,212,255,0.08)"  :
                             state === "danger" ? "rgba(255,45,85,0.08)"  : "transparent",
              boxShadow:     state === "active" ? "0 0 20px rgba(0,212,255,0.15)" :
                             state === "danger" ? "0 0 20px rgba(255,45,85,0.25)" : "none",
              animation:     state === "danger" ? "flashBorder 1s infinite" : "none",
            }}>
              <span>{state === "done" ? "✓" : s.icon}</span>
              <span>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <span style={{
                color: i < step ? "var(--green)" : "var(--dim)",
                padding:"0 4px", fontSize:14,
              }}>→</span>
            )}
          </div>
        );
      })}

      <style>{`
        @keyframes flashBorder {
          0%,100% { box-shadow: 0 0 10px rgba(255,45,85,0.3); }
          50%      { box-shadow: 0 0 25px rgba(255,45,85,0.7); }
        }
      `}</style>
    </div>
  );
}

const styles = {
  bar: {
    gridColumn:"1 / -1",
    background:"var(--panel)",
    padding:"14px 20px",
    display:"flex", alignItems:"center",
    gap:0, overflowX:"auto",
  },
  step: {
    display:"flex", alignItems:"center", gap:8,
    padding:"8px 14px",
    border:"1px solid",
    borderRadius:2,
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, letterSpacing:1,
    cursor:"default",
    whiteSpace:"nowrap",
    transition:"all 0.3s",
  },
};
