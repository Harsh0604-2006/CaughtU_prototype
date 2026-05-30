import { useEffect, useState } from "react";
import { getRankedCves } from "../api.js";

export default function AttackVectorList({ activeAttack }) {
  const [vectors, setVectors] = useState([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getRankedCves("prod").then(data => {
      const rankedVectors = Array.isArray(data?.attack_vectors) ? data.attack_vectors : [];
      setVectors(rankedVectors.slice(0, 5));
      setSummary(data?.executive_summary || "");
      setLoading(false);
    }).catch(err => {
      console.error("Failed to fetch ranked CVEs", err);
      setLoading(false);
    });
  }, []);

  return (
    <section className="panel vector-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Threat Intel</p>
          <h3>Attack Vectors</h3>
        </div>
        <span className="panel-chip red">Ranked CVEs</span>
      </div>

      {summary && (
        <div style={{
          marginTop: "12px",
          marginBottom: "6px",
          padding: "10px 12px",
          borderRadius: "14px",
          background: "rgba(255,45,85,0.04)",
          border: "1px solid rgba(255,45,85,0.14)",
          color: "var(--text-secondary)",
          fontSize: "11px",
          lineHeight: 1.5,
        }}>
          {summary}
        </div>
      )}

      <div className="vector-list">
        {loading && (
          <div style={{ padding: "10px", color: "#6b7280", textAlign: "center" }}>
            Ranking CVEs from backend...
          </div>
        )}

        {!loading && vectors.map((item, index) => {
          const cveId = item.entry_cve || item.cve_id || "Unknown CVE";
          const active = activeAttack?.via === cveId;
          return (
            <article className={`vector-item ${active ? "active" : ""}`} key={item.id || `${cveId}-${index}`}>
              <div>
                <strong>#{item.rank || index + 1} {cveId}</strong>
                <span>{item.target_server || item.name || item.product_mapped || "Service"}</span>
                {item.strategy && (
                  <small style={{
                    display: "block",
                    marginTop: "4px",
                    color: "var(--text-secondary)",
                    fontSize: "11px",
                    lineHeight: 1.4,
                  }}>
                    {item.strategy}
                  </small>
                )}
              </div>
              <div className="score-block">
                <small>CVSS</small>
                <b>{item.cvss_score || item.exploitability_score || "N/A"}</b>
              </div>
            </article>
          );
        })}
        {!loading && vectors.length === 0 && (
          <div style={{ padding: "10px", color: "#6b7280", textAlign: "center" }}>
            No ranked CVEs found.
          </div>
        )}
      </div>
    </section>
  );
}
