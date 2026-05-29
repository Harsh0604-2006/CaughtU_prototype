import { useEffect, useRef, useState } from "react";
import neo4j from "neo4j-driver";
import { Network, DataSet } from "vis-network/standalone";

/* ─── Helpers ──────────────────────────────────────────────── */

function colorFromLabel(label = "") {
  const palette = [
    "#00E5FF", // Neon Cyan
    "#8B5CF6", // Purple Glow
    "#22FF99", // Neon Green
    "#F59E0B", // Cyber Amber
    "#EC4899", // Cyber Pink
    "#3B82F6", // Neon Blue
    "#10B981", // Emerald
    "#FF2D55", // Neon Red
  ];
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = (hash * 31 + label.charCodeAt(i)) >>> 0;
  }
  return palette[hash % palette.length];
}

/** Safely convert a Neo4j Integer (or plain number) to a JS number */
function toNum(v) {
  if (v == null) return 0;
  if (typeof v === "number") return v;
  if (typeof v.toNumber === "function") return v.toNumber();
  if (typeof v.low === "number") return v.low + v.high * 0x100000000;
  return Number(v);
}

/** Create a beautiful, glassmorphic HTML tooltip for a node */
function createNodeTooltip(n, label, state, baseColor) {
  const container = document.createElement("div");
  container.style.padding = "14px 18px";
  container.style.borderRadius = "12px";
  container.style.background = "rgba(18, 21, 31, 0.95)";
  container.style.backdropFilter = "blur(12px)";
  container.style.border = "1px solid rgba(148, 163, 193, 0.2)";
  container.style.boxShadow = `0 12px 32px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(255, 255, 255, 0.05), 0 0 20px ${baseColor}1a`;
  container.style.color = "#E0E7FF";
  container.style.fontFamily = "'Inter', system-ui, sans-serif";
  container.style.fontSize = "12px";
  container.style.pointerEvents = "none";
  container.style.minWidth = "240px";
  container.style.maxWidth = "320px";

  // Label & Status header
  const header = document.createElement("div");
  header.style.display = "flex";
  header.style.justifyContent = "space-between";
  header.style.alignItems = "center";
  header.style.marginBottom = "8px";
  header.style.borderBottom = "1px solid rgba(148, 163, 193, 0.12)";
  header.style.paddingBottom = "6px";

  const labelSpan = document.createElement("span");
  labelSpan.innerText = label.toUpperCase();
  labelSpan.style.color = baseColor;
  labelSpan.style.fontWeight = "800";
  labelSpan.style.fontSize = "9px";
  labelSpan.style.letterSpacing = "1.5px";
  labelSpan.style.fontFamily = "'JetBrains Mono', monospace";

  const stateSpan = document.createElement("span");
  const displayState = state || "normal";
  stateSpan.innerText = displayState.toUpperCase();
  stateSpan.style.fontSize = "9px";
  stateSpan.style.padding = "2px 6px";
  stateSpan.style.borderRadius = "4px";
  stateSpan.style.fontWeight = "bold";
  stateSpan.style.fontFamily = "'JetBrains Mono', monospace";
  
  if (displayState === "compromised") {
    stateSpan.style.background = "rgba(255, 45, 85, 0.15)";
    stateSpan.style.color = "#FF2D55";
    stateSpan.style.border = "1px solid rgba(255, 45, 85, 0.35)";
  } else if (displayState === "fixed") {
    stateSpan.style.background = "rgba(34, 255, 153, 0.15)";
    stateSpan.style.color = "#22FF99";
    stateSpan.style.border = "1px solid rgba(34, 255, 153, 0.35)";
  } else if (displayState === "attention") {
    stateSpan.style.background = "rgba(245, 158, 11, 0.15)";
    stateSpan.style.color = "#f59e0b";
    stateSpan.style.border = "1px solid rgba(245, 158, 11, 0.35)";
  } else {
    stateSpan.style.background = "rgba(0, 229, 255, 0.1)";
    stateSpan.style.color = "#00E5FF";
    stateSpan.style.border = "1px solid rgba(0, 229, 255, 0.25)";
  }

  header.appendChild(labelSpan);
  header.appendChild(stateSpan);
  container.appendChild(header);

  // Name / ID
  const nameDiv = document.createElement("div");
  nameDiv.innerText = n.properties.name || label;
  nameDiv.style.fontSize = "14px";
  nameDiv.style.fontWeight = "600";
  nameDiv.style.color = "#ffffff";
  nameDiv.style.fontFamily = "'Space Grotesk', sans-serif";
  nameDiv.style.marginBottom = "10px";
  container.appendChild(nameDiv);

  // Details list
  const propsList = document.createElement("div");
  propsList.style.display = "flex";
  propsList.style.flexDirection = "column";
  propsList.style.gap = "5px";

  let hasProps = false;
  for (const [key, val] of Object.entries(n.properties)) {
    if (key === "name" || key === "id") continue;
    hasProps = true;

    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.justifyContent = "space-between";
    row.style.gap = "16px";

    const keySpan = document.createElement("span");
    keySpan.innerText = key.replace(/([A-Z])/g, " $1").toLowerCase();
    keySpan.style.color = "#94A3C1";
    keySpan.style.fontSize = "10px";
    keySpan.style.textTransform = "capitalize";

    const valSpan = document.createElement("span");
    valSpan.innerText = String(val);
    valSpan.style.color = "#E0E7FF";
    valSpan.style.fontSize = "10px";
    valSpan.style.fontFamily = "'JetBrains Mono', monospace";
    valSpan.style.wordBreak = "break-all";
    valSpan.style.textAlign = "right";

    row.appendChild(keySpan);
    row.appendChild(valSpan);
    propsList.appendChild(row);
  }

  if (hasProps) {
    container.appendChild(propsList);
  }

  return container;
}

/** Create a beautiful, glassmorphic HTML tooltip for an edge */
function createEdgeTooltip(r) {
  const container = document.createElement("div");
  container.style.padding = "10px 14px";
  container.style.borderRadius = "10px";
  container.style.background = "rgba(18, 21, 31, 0.95)";
  container.style.backdropFilter = "blur(12px)";
  container.style.border = "1px solid rgba(139, 92, 246, 0.25)";
  container.style.boxShadow = "0 12px 28px rgba(0, 0, 0, 0.6), 0 0 1px 1px rgba(255, 255, 255, 0.05)";
  container.style.color = "#E0E7FF";
  container.style.fontFamily = "'Inter', system-ui, sans-serif";
  container.style.fontSize = "11px";
  container.style.pointerEvents = "none";
  container.style.minWidth = "180px";

  const header = document.createElement("div");
  header.innerText = "RELATIONSHIP";
  header.style.color = "#8B5CF6";
  header.style.fontWeight = "800";
  header.style.fontSize = "8px";
  header.style.letterSpacing = "1.5px";
  header.style.marginBottom = "4px";
  header.style.fontFamily = "'JetBrains Mono', monospace";
  container.appendChild(header);

  const typeDiv = document.createElement("div");
  typeDiv.innerText = r.type;
  typeDiv.style.fontSize = "13px";
  typeDiv.style.fontWeight = "600";
  typeDiv.style.color = "#ffffff";
  typeDiv.style.fontFamily = "'Space Grotesk', sans-serif";
  container.appendChild(typeDiv);

  if (r.properties && Object.keys(r.properties).length > 0) {
    const divider = document.createElement("div");
    divider.style.height = "1px";
    divider.style.background = "rgba(148, 163, 193, 0.12)";
    divider.style.margin = "6px 0";
    container.appendChild(divider);

    const propsList = document.createElement("div");
    propsList.style.display = "flex";
    propsList.style.flexDirection = "column";
    propsList.style.gap = "4px";

    for (const [key, val] of Object.entries(r.properties)) {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.style.gap = "12px";

      const keySpan = document.createElement("span");
      keySpan.innerText = key;
      keySpan.style.color = "#94A3C1";
      keySpan.style.fontSize = "9px";

      const valSpan = document.createElement("span");
      valSpan.innerText = String(val);
      valSpan.style.color = "#E0E7FF";
      valSpan.style.fontSize = "9px";
      valSpan.style.fontFamily = "'JetBrains Mono', monospace";

      row.appendChild(keySpan);
      row.appendChild(valSpan);
      propsList.appendChild(row);
    }
    container.appendChild(propsList);
  }

  return container;
}

/* ─── Component ────────────────────────────────────────────── */

export default function DatabaseGraph({ nodeStates = {}, activeAttack }) {
  const containerRef  = useRef(null);
  const networkRef    = useRef(null);
  const nodesDS       = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [stats,   setStats]   = useState({ nodes: 0, edges: 0 });

  /* ── Initial render ── */
  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    const rawUri   = import.meta.env.VITE_NEO4J_URI      || "";
    const user     = import.meta.env.VITE_NEO4J_USER     || "neo4j";
    const password = import.meta.env.VITE_NEO4J_PASSWORD || "";

    if (!rawUri || !user || !password) {
      setLoading(false);
      setError("Missing VITE_NEO4J_URI / _USER / _PASSWORD in .env");
      return;
    }

    const driver  = neo4j.driver(rawUri, neo4j.auth.basic(user, password));
    const session = driver.session(); // AuraDB: do NOT specify database name

    async function fetchAndRender() {
      try {
        const result = await session.run(
          "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 300"
        );

        if (cancelled) return;

        const nodesMap = new Map(); // id → vis node obj
        const edgesMap = new Map(); // id → vis edge obj

        for (const record of result.records) {
          const n = record.get("n");
          const r = record.get("r");
          const m = record.get("m");

          /* -- source node -- */
          processNode(n, nodesMap, nodeStates);
          /* -- target node -- */
          processNode(m, nodesMap, nodeStates);

          /* -- relationship / edge -- */
          const eId = toNum(r.identity);
          if (!edgesMap.has(eId)) {
            edgesMap.set(eId, {
              id:    eId,
              from:  toNum(r.start),
              to:    toNum(r.end),
              label: r.type,
              title: createEdgeTooltip(r),
              arrows: { to: { enabled: true, scaleFactor: 0.95 } },
              color: {
                color: "rgba(186, 230, 253, 0.65)", // Highly visible bright light-blue edge & arrows
                highlight: "#00E5FF", // Vibrant cyan on selection
                hover: "#22FF99" // Vibrant green on hover
              },
              width: 1.5,
              selectionWidth: 3,
              hoverWidth: 3,
              font: {
                color: "rgba(224, 231, 255, 0.75)",
                size: 9,
                face: "JetBrains Mono, monospace",
                strokeWidth: 2,
                strokeColor: "#0A0C12",
                align: "horizontal", // curve-aligned font
              },
              smooth: { enabled: true, type: "continuous", roundness: 0.4 },
            });
          }
        }

        if (cancelled) return;

        const nodes = new DataSet([...nodesMap.values()]);
        const edges = new DataSet([...edgesMap.values()]);
        nodesDS.current = nodes;

        setStats({ nodes: nodesMap.size, edges: edgesMap.size });

        const network = new Network(
          containerRef.current,
          { nodes, edges },
          {
            physics: {
              enabled: true,
              solver: "forceAtlas2Based",
              forceAtlas2Based: {
                gravitationalConstant: -450, // increased negative gravity to accommodate size 48 nodes perfectly with zero overlap
                centralGravity: 0.005,
                springLength: 320,
                springConstant: 0.015,
                damping: 0.55,
              },
              stabilization: { iterations: 150, fit: true },
              minVelocity: 0.75,
            },
            interaction: {
              hover: true,
              tooltipDelay: 150, // faster tooltip reaction
              zoomView: true,
              dragView: true,
            },
          }
        );

        networkRef.current = network;

        network.once("stabilizationIterationsDone", () => {
          if (!cancelled) {
            setLoading(false);
            // Elegantly fit all nodes perfectly in the viewport with a smooth animation
            setTimeout(() => {
              network.fit({
                animation: { duration: 1200, easingFunction: "easeOutQuint" }
              });
            }, 200);
          }
        });
        // Safety fallback
        setTimeout(() => {
          if (!cancelled) {
            setLoading(false);
            network.fit({
              animation: { duration: 1200, easingFunction: "easeOutQuint" }
            });
          }
        }, 4000);

      } catch (e) {
        console.error("Neo4j fetch error:", e);
        if (!cancelled) {
          setLoading(false);
          setError(e?.message || "Connection failed");
        }
      } finally {
        await session.close().catch(() => {});
        await driver.close().catch(() => {});
      }
    }

    fetchAndRender();

    return () => {
      cancelled = true;
      networkRef.current?.destroy();
      networkRef.current = null;
      session.close().catch(() => {});
      driver.close().catch(() => {});
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── React to nodeStates changes ── */
  useEffect(() => {
    if (!nodesDS.current) return;
    try {
      const updates = nodesDS.current.get().map((node) => {
        const state = nodeStates[node.label];
        const color =
          state === "compromised" ? "#ff2d55" :
          state === "fixed"       ? "#22ff99" :
          state === "attention"   ? "#f59e0b" :
          node._baseColor;
        return {
          id: node.id,
          color: {
            background: color + "22",
            border: color,
            highlight: { background: color + "55", border: "#ffffff" },
            hover: { background: color + "33", border: color }
          },
          shadow: {
            enabled: true,
            color: color,
            size: 15,
            x: 0,
            y: 0
          },
          title: createNodeTooltip(node._nObj, node._label, state, color)
        };
      });
      if (updates.length) nodesDS.current.update(updates);
    } catch (e) {
      console.warn("Node color update failed:", e);
    }
  }, [nodeStates]);

  /* ─── Render ─── */
  return (
    <section className="panel database-panel" style={{ overflow: "visible" }}>
      <style>{`
        /* Custom Tooltip Styling for a Stunning Glassmorphism Overlay */
        div.vis-tooltip {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          position: absolute !important;
          visibility: hidden;
          opacity: 0;
          transition: opacity 0.18s cubic-bezier(0.4, 0, 0.2, 1), transform 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
          transform: translateY(6px) scale(0.96) !important;
          z-index: 9999 !important;
          pointer-events: none !important;
        }
        div.vis-tooltip.vis-visible {
          visibility: visible !important;
          opacity: 1 !important;
          transform: translateY(0) scale(1) !important;
        }
      `}</style>
      <div className="panel-header">
        <div>
          <p className="eyebrow">NEO4J DATABASE GRAPH</p>
          <h2>Infrastructure Attack Map</h2>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {!loading && !error && (
            <span style={{
              fontSize: "10px", color: "var(--text-secondary)",
              fontFamily: "JetBrains Mono, monospace",
            }}>
              {stats.nodes} nodes · {stats.edges} edges
            </span>
          )}
          <span className="live-pill">LIVE</span>
        </div>
      </div>

      <div className="graph-area" style={{ position: "relative" }}>
        {loading && (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            color: "var(--text-secondary)", fontSize: "12px",
            fontFamily: "JetBrains Mono, monospace", zIndex: 5,
          }}>
            Connecting to Neo4j…
          </div>
        )}
        {error && (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            color: "var(--red)", fontSize: "12px",
            fontFamily: "JetBrains Mono, monospace",
            zIndex: 5, flexDirection: "column", gap: "8px",
          }}>
            <span>⚠ {error}</span>
            <span style={{ color: "var(--text-secondary)", fontSize: "11px" }}>
              Check browser console for details
            </span>
          </div>
        )}
        <div
          ref={containerRef}
          style={{ width: "100%", height: "650px", minHeight: "650px" }}
        />
      </div>
    </section>
  );
}

/* ─── Node builder (extracted to keep render fn clean) ──── */
function processNode(n, nodesMap, nodeStates) {
  const nId    = toNum(n.identity);
  if (nodesMap.has(nId)) return;

  const label  = n.labels[0] || "";
  const name   = n.properties.name || label;
  const state  = nodeStates[name];
  const base   = colorFromLabel(label);
  const color  =
    state === "compromised" ? "#ff2d55" :
    state === "fixed"       ? "#22ff99" :
    state === "attention"   ? "#f59e0b" :
    base;

  nodesMap.set(nId, {
    id:    nId,
    label: name,
    title: createNodeTooltip(n, label, state, color),
    _baseColor: base,
    _nObj: n,
    _label: label,
    shape: "dot",
    size:  48, // Extra large prominent node size
    color: {
      background: color + "22", // cyber glassmorphic center
      border: color,
      highlight: { background: color + "55", border: "#ffffff" },
      hover: { background: color + "33", border: color }
    },
    shadow: {
      enabled: true,
      color: color, // matching colored glow
      size: 15,
      x: 0,
      y: 0
    },
    font: {
      color: "#ffffff",
      size: 11,
      face: "JetBrains Mono, monospace",
      strokeWidth: 3,
      strokeColor: "#0A0C12",
      vadjust: 6 // push text slightly down from the node
    },
    borderWidth: 2.5,
    borderWidthSelected: 4
  });
}