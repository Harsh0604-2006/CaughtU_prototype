const steps = [
  "Blast Radius",
  "Red Report",
  "Playbook",
  "Approve",
  "Fix Applied",
  "Verified"
];

export default function PipelineBar({ step }) {
  return (
    <section className="pipeline-panel">
      <span className="pipeline-title">Response Pipeline</span>
      <div className="pipeline-steps">
        {steps.map((label, index) => {
          const done = index < step;
          const active = index === step;
          const danger = active && index === 3;

          return (
            <div className="pipeline-group" key={label}>
              <div className={`pipeline-step ${done ? "done" : ""} ${active ? "active" : ""} ${danger ? "danger" : ""}`}>
                <span>{done ? "✓" : String(index + 1).padStart(2, "0")}</span>
                {label}
              </div>
              {index < steps.length - 1 && <span className={`pipeline-arrow ${done ? "done" : ""}`}>→</span>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
