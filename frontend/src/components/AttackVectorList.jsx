import { useEffect, useState } from "react";
import { getVulnerabilities } from "../api.js";

export default function AttackVectorList({ activeAttack }) {
  const [vectors, setVectors] = useState([]);

  useEffect(() => {
    getVulnerabilities("prod").then(data => {
      if (data && data.vulnerabilities) {
        setVectors(data.vulnerabilities.slice(0, 5)); // show top 5
      }
    }).catch(err => console.error("Failed to fetch vulnerabilities", err));
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

      <div className="vector-list">
        {vectors.map((item, index) => {
          const cveId = item.cve_id || "Unknown CVE";
          const active = activeAttack?.via === cveId;
          return (
            <article className={`vector-item ${active ? "active" : ""}`} key={item.id || `${cveId}-${index}`}>
              <div>
                <strong>{cveId}</strong>
                <span>{item.name || item.product_mapped || "Service"}</span>
              </div>
              <div className="score-block">
                <small>CVSS</small>
                <b>{item.cvss_score || "N/A"}</b>
              </div>
            </article>
          );
        })}
        {vectors.length === 0 && (
          <div style={{ padding: "10px", color: "#6b7280", textAlign: "center" }}>
            No vulnerabilities found or loading...
          </div>
        )}
      </div>
    </section>
  );
}
