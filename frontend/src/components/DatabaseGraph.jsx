import { edges, nodes } from "../data/mockData.js";

export default function DatabaseGraph({ nodeStates = {}, activeAttack }) {
  const getNodeStatus = (nodeId) => {
    if (nodeStates[nodeId]) return nodeStates[nodeId];

    if (activeAttack?.path?.includes(nodeId)) {
      return "attention";
    }

    return "normal";
  };

  const getNodeClass = (node) => {
    const status = getNodeStatus(node.id);

    let className = `graph-node ${node.type || "default"}`;

    if (status === "compromised") className += " compromised";
    if (status === "fixed") className += " fixed";
    if (status === "attention") className += " attention";

    return className;
  };

  return (
    <section className="panel database-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">NEO4J DATABASE GRAPH</p>
          <h2>Infrastructure Attack Map</h2>
        </div>

        <span className="live-pill">LIVE</span>
      </div>

      <div className="graph-area">
        <svg className="graph-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
          {edges.map((edge, index) => {
            const sourceNode = nodes.find((node) => node.id === edge.source);
            const targetNode = nodes.find((node) => node.id === edge.target);

            if (!sourceNode || !targetNode) return null;

            const sourceState = getNodeStatus(sourceNode.id);
            const targetState = getNodeStatus(targetNode.id);

            const isHot =
              sourceState === "compromised" ||
              targetState === "compromised" ||
              sourceState === "attention" ||
              targetState === "attention";

            const isFixed =
              sourceState === "fixed" && targetState === "fixed";

            return (
              <line
                key={index}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                className={
                  isFixed
                    ? "graph-link fixed"
                    : isHot
                    ? "graph-link hot"
                    : "graph-link"
                }
              />
            );
          })}
        </svg>

        {nodes.map((node) => (
          <div
            key={node.id}
            className={getNodeClass(node)}
            style={{
              left: `${node.x}%`,
              top: `${node.y}%`,
            }}
            title={`${node.id} - ${node.type}`}
          >
            <span className="node-core"></span>
            <span className="node-label">{node.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}