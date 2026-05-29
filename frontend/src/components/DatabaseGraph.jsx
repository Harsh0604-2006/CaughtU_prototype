import { useEffect, useRef, useState } from "react";
import NeoVis from "neovis.js";

function colorFromLabel(label = "") {
  const palette = [
    "#3b82f6", "#8b5cf6", "#06b6d4", "#10b981",
    "#f59e0b", "#ef4444", "#14b8a6", "#64748b",
  ];
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = (hash * 31 + label.charCodeAt(i)) >>> 0;
  }
  return palette[hash % palette.length];
}

function normalizeUri(rawUri) {
  if (rawUri.startsWith("neo4j+ssc://")) {
    return {
      serverUrl: rawUri.replace("neo4j+ssc://", "neo4j://"),
      driverConfig: { encrypted: "ENCRYPTION_ON", trust: "TRUST_ALL_CERTIFICATES" },
    };
  }
  if (rawUri.startsWith("neo4j+s://")) {
    return {
      serverUrl: rawUri.replace("neo4j+s://", "neo4j://"),
      driverConfig: { encrypted: "ENCRYPTION_ON", trust: "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" },
    };
  }
  if (rawUri.startsWith("bolt+ssc://")) {
    return {
      serverUrl: rawUri.replace("bolt+ssc://", "bolt://"),
      driverConfig: { encrypted: "ENCRYPTION_ON", trust: "TRUST_ALL_CERTIFICATES" },
    };
  }
  if (rawUri.startsWith("bolt+s://")) {
    return {
      serverUrl: rawUri.replace("bolt+s://", "bolt://"),
      driverConfig: { encrypted: "ENCRYPTION_ON", trust: "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" },
    };
  }
  return { serverUrl: rawUri, driverConfig: undefined };
}

export default function DatabaseGraph({ nodeStates = {}, activeAttack }) {
  const containerRef   = useRef(null);
  const vizRef         = useRef(null);
  const renderTimerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const getNodeColor = (node) => {
    const props  = node?.raw?.properties || {};
    const labels = node?.raw?.labels     || [];
    const name   = props.name;
    if (name && nodeStates[name]) {
      const s = nodeStates[name];
      if (s === "compromised") return "#ff2d55";
      if (s === "fixed")       return "#22ff99";
      if (s === "attention")   return "#f59e0b";
    }
    return colorFromLabel(labels[0] || name || "");
  };

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

    if (vizRef.current) {
      try { vizRef.current.clearNetwork(); } catch (_) {}
    }

    const { serverUrl, driverConfig } = normalizeUri(rawUri);

    const neo4jConfig = {
      serverUrl,
      serverUser: user,
      serverPassword: password,
      serverDatabase: "neo4j",
      ...(driverConfig ? { driverConfig } : {}),
    };

    const config = {
      containerId: containerRef.current.id,
      neo4j: neo4jConfig,
      labels: {
        [NeoVis.NEOVIS_DEFAULT_CONFIG]: {
          label: "name",
          size: "risk_score",
          [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
            function: { color: getNodeColor },
          },
        },
      },
      relationships: {
  [NeoVis.NEOVIS_DEFAULT_CONFIG]: {
    caption: true,
    thickness: 5,
  },
},
   
      visConfig: {
        nodes: {
          shape: "dot",
          size: 24,
          font: {
            color: "#ffffff",
            size: 12,
            face: "JetBrains Mono, monospace",
            strokeWidth: 2,        // FIX 2: was missing entirely — needs a small value
            strokeColor: "#0a0c12",
          },
          borderWidth: 2,
        },
        edges: {
          arrows: { to: { enabled: true, scaleFactor: 0.7 } },
          width: 2,
          font: {
  color: "#ffffff",
  size: 14,
            face: "JetBrains Mono, monospace",
            strokeWidth: 2,        // FIX 2: was 4 — thick stroke smears the text into a blur
            strokeColor: "#0a0c12",
            align: "top",
          },
          color: { color: "#94a3b8", highlight: "#f8fafc", hover: "#f43f5e" },
          smooth: { type: "continuous" },
        },
        physics: {
          enabled: true,
          solver: "forceAtlas2Based",
          forceAtlas2Based: {
            gravitationalConstant: -40,
            centralGravity: 0.008,
            springLength: 220,
            springConstant: 0.04,
            damping: 0.4,
          },
          stabilization: { iterations: 80, fit: true },
        },
        interaction: { hover: true, tooltipDelay: 200, zoomView: true, dragView: true },
      },
      initialCypher: `
MATCH (n)
OPTIONAL MATCH (n)-[r]-(m)
RETURN n,r,m
LIMIT 250
`,
    };

    let VizClass = NeoVis;
    if (typeof NeoVis !== "function" && NeoVis.default) VizClass = NeoVis.default;

    const viz = new VizClass(config);

    viz.registerOnEvent("completed", () => {
      clearTimeout(renderTimerRef.current);
      if (!cancelled) { setLoading(false); setError(null); }
    });

    viz.registerOnEvent("error", (e) => {
      clearTimeout(renderTimerRef.current);
      console.error("NeoVis error:", e);
      if (!cancelled) {
        setLoading(false);
        setError(typeof e === "string" ? e : e?.message || "Connection failed");
      }
    });

    vizRef.current = viz;
    viz.render();

    renderTimerRef.current = setTimeout(() => {
      if (!cancelled) setLoading(false);
    }, 1500);

    return () => {
      cancelled = true;
      clearTimeout(renderTimerRef.current);
      try { viz.clearNetwork(); } catch (_) {}
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!vizRef.current) return;
    const dataset =
      vizRef.current.nodes ||
      vizRef.current._network?.body?.data?.nodes;
    if (!dataset) return;

    try {
      const updates = dataset.get().map((node) => {
        const props  = node.raw?.properties || {};
        const labels = node.raw?.labels     || [];
        const name   = props.name || node.label;
        const state  = name && nodeStates[name];
        const color  = state === "compromised" ? "#ff2d55"
                     : state === "fixed"       ? "#22ff99"
                     : state === "attention"   ? "#f59e0b"
                     : colorFromLabel(labels[0] || name || "");
        return { id: node.id, color: { background: color, border: color } };
      });
      if (updates.length) dataset.update(updates);
    } catch (e) {
      console.warn("Node color update failed:", e);
    }
  }, [nodeStates]);

  return (
    <section className="panel database-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">NEO4J DATABASE GRAPH</p>
          <h2>Infrastructure Attack Map</h2>
        </div>
        <span className="live-pill">LIVE (NEOVIS)</span>
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
          id="neovis-container"
          ref={containerRef}
          style={{ width: "100%", height: "100%", minHeight: "400px" }}
        />
      </div>
    </section>
  );
}