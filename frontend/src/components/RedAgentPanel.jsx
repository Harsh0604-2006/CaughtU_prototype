export default function RedAgentPanel({ attack, step }) {
  const reportItems = attack?.redReport || attack?.report || attack?.findings || [];
  const attackPath = attack?.path || [];

  const cveValue = attack?.cve || attack?.via || "Not detected";
  const entryValue = attack?.entry || attack?.target || "Unknown";
  const riskValue = attack?.risk || 0;
  const sourceIpValue = attack?.sourceIp || attack?.ip || "Unknown";

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
          <div className="report-grid">
            <div className="report-item">
              <span>Entry</span>
              <strong>{entryValue}</strong>
            </div>

            <div className="report-item">
              <span>Via</span>
              <strong>{cveValue}</strong>
            </div>

            <div className="report-item">
              <span>Risk</span>
              <strong>{riskValue}/100</strong>
            </div>

            <div className="report-item">
              <span>Source IP</span>
              <strong>{sourceIpValue}</strong>
            </div>
          </div>

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

          <div className="report-list">
            <p className="mini-label">Red Agent Findings</p>

            {reportItems.length > 0 ? (
              reportItems.map((item, index) => (
                <div className="report-line" key={index}>
                  <span className="bullet-dot"></span>
                  <p>{item}</p>
                </div>
              ))
            ) : (
              <div className="report-line">
                <span className="bullet-dot"></span>
                <p>
                  Red Agent detected suspicious activity and generated an
                  attack path for review.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}