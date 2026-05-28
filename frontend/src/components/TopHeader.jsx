export default function TopHeader({ now, status, metrics, onSimulate }) {
  const formattedDate = now.toLocaleDateString("en-IN", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric"
  });

  const formattedTime = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });

  return (
    <header className="top-header">
      <div>
        <div className="eyebrow">Live Security Operations Console</div>
        <h1>CYBER DEFENSE COMMAND</h1>
      </div>

      <div className="header-actions">
        <div className="mini-stat">
          <span>Alerts</span>
          <strong>{metrics.openAlerts}</strong>
        </div>
        <div className="mini-stat">
          <span>Risk</span>
          <strong>{metrics.riskScore}</strong>
        </div>
        <div className={`status-pill ${status === "UNDER ATTACK" ? "danger" : status === "SECURED" ? "safe" : ""}`}>
          <span className="pulse-dot" />
          {status}
        </div>
        <div className="clock-card">
          <span>{formattedDate}</span>
          <strong>{formattedTime}</strong>
        </div>
        <button className="simulate-btn" onClick={onSimulate} type="button">
          Simulate Attack
        </button>
      </div>
    </header>
  );
}
