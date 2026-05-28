import { useEffect, useRef } from "react";

export default function LiveLogs({ logs }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <section className="panel logs-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Live Logs</p>
          <h3>Terminal Stream</h3>
        </div>
        <span className="panel-chip green">Streaming</span>
      </div>

      <div className="terminal-window">
        {logs.map((log) => (
          <p className={`log-line ${log.level}`} key={log.id}>
            <span>[{log.time}]</span>
            <b>{log.level.toUpperCase()}</b>
            {log.text}
          </p>
        ))}
        <div ref={endRef} />
      </div>
    </section>
  );
}
