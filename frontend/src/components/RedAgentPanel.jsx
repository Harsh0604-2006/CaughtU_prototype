export default function RedAgentPanel({ attack, step }) {
  const defensivePriorities = attack?.defensivePriorities || [];
  const attackPath = attack?.path || [];
  const attackSteps = attack?.attackSteps || [];

  const cveValue = attack?.via || "Not detected";
  const entryValue = attack?.entry || "Unknown";
  const riskValue = attack?.risk || 0;
  const sourceIpValue = attack?.sourceIp || "Unknown";
  const blastRadiusCount = attack?.affectedNodes || 0;
  const highestValueTarget = attack?.highestValueTarget || "Unknown";
  const overallSeverity = attack?.overallSeverity || "Unknown";

  return (
    <section className="panel red-agent-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow danger-text">RED AGENT REPORT</p>
          <h2>Attack Narrative</h2>
        </div>

        <span className="status-chip danger">
          {attack ? "Threat Found" : "Listening"}
        </span>
      </div>

      {!attack || step < 1 ? (
        <div className="empty-state">Waiting for simulated attack...</div>
      ) : (
        <div className="red-report-content">
          {/* Key metrics grid */}
          <div className="report-grid">
            <div className="report-item">
              <span>Entry Point</span>
              <strong>{entryValue}</strong>
            </div>

            <div className="report-item">
              <span>CVE Used</span>
              <strong>{cveValue}</strong>
            </div>

            <div className="report-item">
              <span>Risk</span>
              <strong>{riskValue}/100</strong>
            </div>

            <div className="report-item">
              <span>Severity</span>
              <strong style={{
                color: overallSeverity === "CRITICAL" ? "var(--red)" :
                  overallSeverity === "HIGH" ? "#f59e0b" : "var(--text-primary)"
              }}>
                {overallSeverity}
              </strong>
            </div>
          </div>

          {/* Secondary metrics */}
          <div style={{
            display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "14px",
          }}>
            <div style={{
              padding: "6px 14px", borderRadius: "999px",
              background: "rgba(255,45,85,0.1)", border: "1px solid rgba(255,45,85,0.3)",
              fontFamily: "JetBrains Mono, monospace", fontSize: "11px", color: "var(--red)",
            }}>
              Blast Radius: {blastRadiusCount} nodes
            </div>
            <div style={{
              padding: "6px 14px", borderRadius: "999px",
              background: "rgba(255,45,85,0.1)", border: "1px solid rgba(255,45,85,0.3)",
              fontFamily: "JetBrains Mono, monospace", fontSize: "11px", color: "var(--red)",
            }}>
              Target: {highestValueTarget}
            </div>
            <div style={{
              padding: "6px 14px", borderRadius: "999px",
              background: "rgba(255,45,85,0.05)", border: "1px solid rgba(255,45,85,0.2)",
              fontFamily: "JetBrains Mono, monospace", fontSize: "11px", color: "var(--text-secondary)",
            }}>
              Source: {sourceIpValue}
            </div>
          </div>

          {/* Attack path visualization */}
          <div className="attack-path-box">
            <p className="mini-label">Attack Path</p>
            <div className="attack-path">
              {attackPath.length > 0 ? (
                attackPath.map((node, index) => (
                  <span key={`${node}-${index}`}>
                    {node}
                    {index < attackPath.length - 1 ? (
                      <b className="path-arrow">→</b>
                    ) : null}
                  </span>
                ))
              ) : (
                <span>No attack path found</span>
              )}
            </div>
          </div>

          {/* Attack steps from LLM */}
          {attackSteps.length > 0 && (
            <div style={{
              marginBottom: "14px", padding: "12px", borderRadius: "16px",
              border: "1px solid rgba(255,45,85,0.2)", background: "rgba(255,45,85,0.035)",
            }}>
              <p className="mini-label">Attack Steps</p>
              {attackSteps.map((s, i) => (
                <div key={i} style={{
                  display: "flex", gap: "10px", alignItems: "flex-start",
                  padding: "8px 0",
                  borderBottom: i < attackSteps.length - 1 ? "1px solid rgba(148,163,193,0.08)" : "none",
                }}>
                  <span style={{
                    fontFamily: "JetBrains Mono, monospace", fontWeight: 700,
                    color: "var(--red)", fontSize: "12px", flexShrink: 0,
                  }}>
                    {String(s.step || i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p style={{
                      margin: 0, color: "var(--text-primary)", fontSize: "12px",
                      lineHeight: 1.5, wordBreak: "break-word",
                    }}>
                      <strong>{s.action}</strong>
                      {s.target_node && (
                        <span style={{ color: "var(--red)" }}> → {s.target_node}</span>
                      )}
                    </p>
                    {s.result && (
                      <p style={{
                        margin: "4px 0 0", color: "var(--text-secondary)",
                        fontSize: "11px", fontStyle: "italic",
                      }}>
                        {s.result}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Executive summary */}
          <div className="report-list">
            <p className="mini-label">Executive Summary</p>
            <div style={{ padding: "7px 0" }}>
              <p style={{
                margin: 0, color: "var(--text-secondary)", fontSize: "12px",
                lineHeight: 1.6, wordBreak: "break-word",
              }}>
                {attack.executiveSummary || "No summary provided."}
              </p>
            </div>

            {defensivePriorities.length > 0 && (
              <>
                <p className="mini-label" style={{ marginTop: "12px" }}>
                  Recommended Defenses
                </p>
                {defensivePriorities.map((item, index) => (
                  <div className="report-line" key={index}>
                    <span className="bullet-dot" />
                    <p>{item}</p>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}