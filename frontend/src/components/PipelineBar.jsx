const steps = [
  "Blast Radius",
  "Red Report",
  "Playbook",
  "Approve",
  "Fix Applied",
  "Verified",
];

export default function PipelineBar({ step }) {
  return (
    <section className="pipeline-panel">
      <p className="pipeline-title">Response Pipeline</p>

      <div className="pipeline-steps">
        {steps.map((label, index) => {
          let state = "idle";

          if (step >= index) {
            state = "done";
          }

          if (step === index && index !== steps.length - 1) {
            state = index === 3 ? "danger" : "active";
          }

          if (step >= steps.length - 1 && index === steps.length - 1) {
            state = "done";
          }

          return (
            <div className="pipeline-group" key={label}>
              <div className={`pipeline-step ${state}`}>
                <span>{state === "done" ? "✓" : `0${index + 1}`}</span>
                <span>{label}</span>
              </div>

              {index < steps.length - 1 && (
                <span className={`pipeline-arrow ${step > index ? "done" : ""}`}>
                  →
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}