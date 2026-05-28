export default function AgentCard({ type, title, subtitle, status, metricLabel, metricValue, description }) {
  return (
    <article className={`agent-card ${type}`}>
      <div className="agent-glow" />
      <div className="agent-card-header">
        <div>
          <p className="section-kicker">{subtitle}</p>
          <h2>{title}</h2>
        </div>
        <span className="agent-badge">{status}</span>
      </div>

      <p className="agent-description">{description}</p>

      <div className="agent-metric">
        <span>{metricLabel}</span>
        <strong>{metricValue}</strong>
      </div>
    </article>
  );
}
