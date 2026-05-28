export default function BlueAgentPanel({ attack, step, onApprove, responseTime }) {
  const playbook = attack?.playbook || [];

  const canApprove = attack && step >= 3 && step < 4;
  const applyingFix = step === 4;
  const verified = step >= 5;

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
              Approve & Apply Fix
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

          <ul className="playbook-list scroll-list">
            {playbook.map((item, index) => (
              <li key={index} style={{ animationDelay: `${index * 120}ms` }}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{item}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}