export default function TopHeader({ now, status, metrics, onSimulate }) {
  const formattedDate = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  const formattedTime = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

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
        <div className="mini-stat">
          <span>Alerts</span>
          <strong>{metrics?.openAlerts ?? 0}</strong>
        </div>

        <div className="mini-stat">
          <span>Risk</span>
          <strong>{metrics?.riskScore ?? 0}</strong>
        </div>

        <div className={`status-pill ${statusClass}`}>
          <span className="pulse-dot"></span>
          <span>{status}</span>
        </div>

        <div className="clock-card">
          <span>{formattedDate}</span>
          <strong>{formattedTime}</strong>
        </div>

        <button type="button" className="simulate-btn" onClick={onSimulate}>
          Simulate Attack
        </button>
      </div>
    </header>
  );
}