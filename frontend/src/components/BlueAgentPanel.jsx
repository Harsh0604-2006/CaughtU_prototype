export default function BlueAgentPanel({ attack, step, onApprove, responseTime }) {
  const playbookData = attack?.playbook || null;

  const canApprove = attack && step >= 3 && step < 4;
  const applyingFix = step === 4;
  const verified = step >= 5;

  // Extract structured playbook steps from the backend response
  let playbookSteps = playbookData?.playbook || [];
  let validationChecklist = playbookData?.validation_checklist || [];
  
  if (typeof playbookSteps === "string") {
    try {
      // Sometimes LLM returns raw JSON wrapped in markdown or just stringified
      const cleanStr = playbookSteps.replace(/^```json/i, "").replace(/```$/, "").trim();
      playbookSteps = JSON.parse(cleanStr);
    } catch (e) {
      console.warn("Failed to parse playbook JSON", e);
    }
  }

  if (typeof validationChecklist === "string") {
    try {
      const cleanStr = validationChecklist.replace(/^```json/i, "").replace(/```$/, "").trim();
      validationChecklist = JSON.parse(cleanStr);
    } catch (e) {
      // If it's a simple string list, make it an array
      validationChecklist = validationChecklist.split("\n").filter(Boolean);
    }
  }

  const totalTime = playbookData?.total_remediation_time || null;
  const riskBefore = playbookData?.risk_level_before || null;
  const riskAfter = playbookData?.risk_level_after || null;
  const severityLevel = playbookData?.severity_level || null;
  const riskScore = playbookData?.risk_score || null;

  // Group steps by phase
  const phases = {};
  if (Array.isArray(playbookSteps)) {
    playbookSteps.forEach(s => {
      const phase = s.phase || "GENERAL";
      if (!phases[phase]) phases[phase] = [];
      phases[phase].push(s);
    });
  }

  const phaseOrder = ["IMMEDIATE", "SHORT-TERM", "LONG-TERM", "GENERAL"];
  const phaseColors = {
    "IMMEDIATE": "var(--red)",
    "SHORT-TERM": "var(--yellow, #f59e0b)",
    "LONG-TERM": "var(--cyan)",
    "GENERAL": "var(--text-secondary)",
  };

  return (
    <section className="panel blue-agent-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow cyan-text">BLUE AGENT PLAYBOOK</p>
          <h2>Remediation Plan</h2>
        </div>
        <span className="panel-chip cyan">Defensive View</span>
      </div>

      {!attack || step < 2 ? (
        <div className="empty-state">Awaiting Red Agent report...</div>
      ) : (
        <div className="blue-panel-body">
          {canApprove && (
            <button
              type="button"
              className="approve-button approve-visible"
              onClick={onApprove}
            >
              Approve &amp; Apply Fix
            </button>
          )}

          {applyingFix && (
            <div className="approval-banner working">
              Applying remediation sequence...
            </div>
          )}

          {verified && (
            <div className="approval-banner complete">
              Verified clean in {responseTime || "4.1"}s
            </div>
          )}

          {/* Risk summary bar */}
          {(riskScore || severityLevel || totalTime) && (
            <div style={{
              display: "flex", gap: "12px", flexWrap: "wrap",
              marginTop: "16px", marginBottom: "8px",
            }}>
              {severityLevel && (
                <div style={{
                  padding: "6px 14px", borderRadius: "999px",
                  background: severityLevel === "CRITICAL" ? "rgba(255,45,85,0.15)" :
                    severityLevel === "HIGH" ? "rgba(245,158,11,0.15)" : "rgba(0,229,255,0.1)",
                  border: `1px solid ${severityLevel === "CRITICAL" ? "rgba(255,45,85,0.4)" :
                    severityLevel === "HIGH" ? "rgba(245,158,11,0.4)" : "rgba(0,229,255,0.3)"}`,
                  color: severityLevel === "CRITICAL" ? "var(--red)" :
                    severityLevel === "HIGH" ? "#f59e0b" : "var(--cyan)",
                  fontFamily: "JetBrains Mono, monospace", fontSize: "11px", fontWeight: 700,
                }}>
                  {severityLevel}
                </div>
              )}
              {riskScore > 0 && (
                <div style={{
                  padding: "6px 14px", borderRadius: "999px",
                  background: "rgba(0,229,255,0.08)", border: "1px solid rgba(0,229,255,0.25)",
                  color: "var(--cyan)", fontFamily: "JetBrains Mono, monospace", fontSize: "11px",
                }}>
                  Risk: {riskScore}
                </div>
              )}
              {totalTime && (
                <div style={{
                  padding: "6px 14px", borderRadius: "999px",
                  background: "rgba(34,255,153,0.08)", border: "1px solid rgba(34,255,153,0.25)",
                  color: "var(--green)", fontFamily: "JetBrains Mono, monospace", fontSize: "11px",
                }}>
                  ETA: {totalTime}
                </div>
              )}
              {riskBefore && riskAfter && (
                <div style={{
                  padding: "6px 14px", borderRadius: "999px",
                  background: "rgba(34,255,153,0.08)", border: "1px solid rgba(34,255,153,0.25)",
                  color: "var(--green)", fontFamily: "JetBrains Mono, monospace", fontSize: "11px",
                }}>
                  {riskBefore} → {riskAfter}
                </div>
              )}
            </div>
          )}

          {/* Playbook steps grouped by phase */}
          <div className="playbook-content scroll-list" style={{
            textAlign: "left", padding: "10px", color: "var(--text-color)",
            overflowY: "auto",
          }}>
            {Object.keys(phases).length > 0 ? (
              phaseOrder
                .filter(phase => phases[phase])
                .map(phase => (
                  <div key={phase} style={{ marginBottom: "20px" }}>
                    <div style={{
                      display: "flex", alignItems: "center", gap: "10px",
                      marginBottom: "12px", paddingBottom: "6px",
                      borderBottom: `1px solid ${phaseColors[phase] || "var(--border)"}33`,
                    }}>
                      <span style={{
                        display: "inline-block", width: "8px", height: "8px",
                        borderRadius: "50%", background: phaseColors[phase] || "var(--cyan)",
                        boxShadow: `0 0 10px ${phaseColors[phase] || "var(--cyan)"}`,
                      }} />
                      <span style={{
                        fontFamily: "JetBrains Mono, monospace", fontSize: "11px",
                        fontWeight: 700, textTransform: "uppercase", letterSpacing: "1.5px",
                        color: phaseColors[phase] || "var(--text-secondary)",
                      }}>
                        {phase}
                      </span>
                    </div>

                    {phases[phase].map((item, idx) => (
                      <div key={idx} style={{
                        marginBottom: "12px", padding: "14px",
                        borderRadius: "14px", borderLeft: `3px solid ${phaseColors[phase] || "var(--cyan)"}`,
                        background: "rgba(10,12,18,0.4)",
                        animation: `revealStep 420ms ease forwards`,
                        animationDelay: `${idx * 120}ms`, opacity: 0,
                      }}>
                        <div style={{
                          display: "flex", justifyContent: "space-between",
                          alignItems: "flex-start", marginBottom: "8px",
                        }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span style={{
                              fontFamily: "JetBrains Mono, monospace", fontWeight: 700,
                              color: "var(--cyan)", fontSize: "13px",
                            }}>
                              {String(item.step || idx + 1).padStart(2, "0")}
                            </span>
                            {item.responsible_team && (
                              <span style={{
                                padding: "2px 8px", borderRadius: "999px",
                                background: "rgba(0,229,255,0.1)", border: "1px solid rgba(0,229,255,0.2)",
                                fontFamily: "JetBrains Mono, monospace", fontSize: "9px",
                                color: "var(--cyan)", textTransform: "uppercase",
                              }}>
                                {item.responsible_team}
                              </span>
                            )}
                          </div>
                          {item.estimated_time && (
                            <span style={{
                              fontFamily: "JetBrains Mono, monospace", fontSize: "10px",
                              color: "var(--text-secondary)",
                            }}>
                              ⏱ {item.estimated_time}
                            </span>
                          )}
                        </div>

                        <p style={{
                          margin: 0, color: "var(--text-primary)", fontSize: "12px",
                          lineHeight: 1.6, wordBreak: "break-word",
                        }}>
                          {item.action}
                        </p>

                        {item.success_criteria && (
                          <details style={{ marginTop: "8px" }}>
                            <summary style={{
                              cursor: "pointer", fontFamily: "JetBrains Mono, monospace",
                              fontSize: "10px", color: "var(--green)",
                              textTransform: "uppercase", letterSpacing: "1px",
                            }}>
                              Success Criteria
                            </summary>
                            <p style={{
                              margin: "6px 0 0", fontSize: "11px", lineHeight: 1.5,
                              color: "var(--text-secondary)", wordBreak: "break-word",
                            }}>
                              {item.success_criteria}
                            </p>
                          </details>
                        )}

                        {item.rollback_procedure && (
                          <details style={{ marginTop: "6px" }}>
                            <summary style={{
                              cursor: "pointer", fontFamily: "JetBrains Mono, monospace",
                              fontSize: "10px", color: "var(--yellow, #f59e0b)",
                              textTransform: "uppercase", letterSpacing: "1px",
                            }}>
                              Rollback Procedure
                            </summary>
                            <p style={{
                              margin: "6px 0 0", fontSize: "11px", lineHeight: 1.5,
                              color: "var(--text-secondary)", wordBreak: "break-word",
                            }}>
                              {item.rollback_procedure}
                            </p>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                ))
            ) : playbookData?.raw_response ? (
              <div style={{
                color: "var(--text-secondary)", fontSize: "12px",
                lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>
                {playbookData.raw_response}
              </div>
            ) : (
              <div className="empty-state">Generating playbook...</div>
            )}
          </div>

          {/* Validation checklist */}
          {validationChecklist.length > 0 && (
            <div style={{
              marginTop: "16px", padding: "12px", borderRadius: "14px",
              border: "1px dashed rgba(34,255,153,0.25)", background: "rgba(34,255,153,0.03)",
            }}>
              <p style={{
                margin: "0 0 10px", fontFamily: "JetBrains Mono, monospace",
                fontSize: "10px", color: "var(--green)", textTransform: "uppercase",
                letterSpacing: "1.5px",
              }}>
                Validation Checklist
              </p>
              {validationChecklist.map((item, i) => (
                <div key={i} style={{
                  display: "flex", gap: "8px", alignItems: "flex-start",
                  padding: "4px 0", fontSize: "11px", color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}>
                  <span style={{ color: "var(--green)", fontWeight: 700, flexShrink: 0 }}>✓</span>
                  <span style={{ wordBreak: "break-word" }}>{item}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}