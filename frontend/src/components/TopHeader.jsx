export default function TopHeader({ now, status, metrics, onSimulate }) {
  const statusClass =
    status === "UNDER ATTACK"
      ? "danger"
      : status === "SECURED"
        ? "safe"
        : "";

  return (
    <header className="top-header">
      <div>
        <p className="eyebrow">LIVE SECURITY OPERATIONS CONSOLE</p>
        <h1>CAUGHTU!</h1>
      </div>

      <div className="header-actions">
        <div className={`status-pill ${statusClass}`}>
          <span className="pulse-dot"></span>
          <span>{status}</span>
        </div>

        <button
          type="button"
          className="simulate-btn"
          onClick={onSimulate}
          disabled={status === "ANALYZING"}
          style={{ opacity: status === "ANALYZING" ? 0.7 : 1, cursor: status === "ANALYZING" ? "not-allowed" : "pointer" }}
        >
          {status === "ANALYZING" ? "Simulating Attack..." : "Simulate Attack"}
        </button>
      </div>
    </header>
  );
}