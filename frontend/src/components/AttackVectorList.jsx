import { attackVectors } from "../data/mockData.js";

export default function AttackVectorList({ activeAttack }) {
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
        {attackVectors.map((item) => {
          const active = activeAttack?.cve === item.cve;
          return (
            <article className={`vector-item ${active ? "active" : ""}`} key={item.cve}>
              <div>
                <strong>{item.cve}</strong>
                <span>{item.service}</span>
              </div>
              <div className="score-block">
                <small>{item.priority}</small>
                <b>{item.score}</b>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
