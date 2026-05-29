import { useEffect, useRef, useState } from "react";
import NeoVis from "neovis.js";

export default function DatabaseGraph({ nodeStates = {}, activeAttack }) {
  const containerRef = useRef(null);
  const vizRef = useRef(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;

    async function initGraph() {
      try {
        if (cancelled) return;

        // Clean up previous instance
        if (vizRef.current) {
          try { vizRef.current.clearNetwork(); } catch (_) {}
        }

        const neo4jUri = import.meta.env.VITE_NEO4J_URI || "";
        const neo4jUser = import.meta.env.VITE_NEO4J_USER || "";
        const neo4jPassword = import.meta.env.VITE_NEO4J_PASSWORD || "";

        // Use the original neo4j+s:// URL as-is
        // The +s suffix tells the driver to use encryption — no separate driverConfig needed
        const serverUrl = neo4jUri;

        // Build node color function based on nodeStates
        const getNodeColor = (node) => {
          const name = node.properties?.name;
          if (name && nodeStates[name]) {
            const state = nodeStates[name];
            if (state === "compromised") return "#ff2d55";
            if (state === "fixed") return "#22ff99";
            if (state === "attention") return "#f59e0b";
          }

          // Color by label type
          const labels = node.labels || [];
          if (labels.some(l => /bank|core|api|gateway/i.test(l))) return "#3b82f6";
          if (labels.some(l => /server|datacenter|infrastructure/i.test(l))) return "#8b5cf6";
          if (labels.some(l => /compliance|security|fraud|audit/i.test(l))) return "#f59e0b";
          if (labels.some(l => /customer|employee/i.test(l))) return "#06b6d4";
          if (labels.some(l => /account|loan|transaction/i.test(l))) return "#22ff99";
          return "#6b7280";
        };

        const config = {
          containerId: containerRef.current.id,
          neo4j: {
            serverUrl,
            serverUser: neo4jUser,
            serverPassword: neo4jPassword,
            serverDatabase: "neo4j",
          },
          visConfig: {
            nodes: {
              shape: "dot",
              size: 18,
              font: {
                color: "#ffffff",
                size: 11,
                face: "JetBrains Mono, monospace",
              },
              borderWidth: 2,
            },
            edges: {
              arrows: { to: { enabled: true, scaleFactor: 0.5 } },
              color: { color: "#4b5563", highlight: "#ef4444" },
              smooth: { type: "continuous" },
            },
            physics: {
              enabled: true,
              solver: "forceAtlas2Based",
              forceAtlas2Based: {
                gravitationalConstant: -40,
                centralGravity: 0.008,
                springLength: 120,
                springConstant: 0.04,
                damping: 0.4,
              },
              stabilization: { iterations: 80, fit: true },
            },
            interaction: {
              hover: true,
              tooltipDelay: 200,
              zoomView: true,
              dragView: true,
            },
          },
          labels: {
            // Use a wildcard-like approach: configure common labels
            // NeoVis will pick up any label that matches
          },
          relationships: {},
          // Query ALL nodes and their relationships - schema agnostic
          initialCypher: `
            MATCH (n)
            WHERE n.name IS NOT NULL
            OPTIONAL MATCH (n)-[r]-(m)
            WHERE m.name IS NOT NULL
            RETURN n, r, m
            LIMIT 200
          `,
        };

        // Dynamically add label configs for all known banking graph labels
        const knownLabels = [
          "DataCenter", "ComplianceModule", "Customer", "Employee",
          "Account", "Loan", "Server", "CoreBankingAPI", "APIGateway",
          "PaymentGateway", "UPIGateway", "TreasuryServer", "DatabaseServer",
          "MessageBroker", "SecurityModule", "NetworkDevice", "Application",
          "BankingNode", "Infrastructure", "Service"
        ];

        knownLabels.forEach(label => {
          config.labels[label] = {
            label: "name",
            [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
              function: {
                color: getNodeColor,
              },
            },
          };
        });

        let VizClass = NeoVis;
        if (typeof NeoVis !== 'function' && NeoVis.default) {
          VizClass = NeoVis.default;
        }
        
        const viz = new VizClass(config);

        viz.registerOnEvent("completed", () => {
          if (!cancelled) {
            setLoading(false);
            setError(null);
          }
        });

        viz.registerOnEvent("error", (e) => {
          console.error("NeoVis error:", e);
          if (!cancelled) {
            setLoading(false);
            setError("Failed to connect to Neo4j database");
          }
        });

        vizRef.current = viz;
        viz.render();
      } catch (err) {
        console.error("Error initializing NeoVis:", err);
        if (!cancelled) {
          setLoading(false);
          setError(err.message || "Failed to load graph visualization");
        }
      }
    }

    setLoading(true);
    setError(null);
    initGraph();

    return () => {
      cancelled = true;
    };
  }, []); // Only init once!

  // Dynamically update node colors without recreating the graph
  useEffect(() => {
    if (!vizRef.current) return;
    
    const viz = vizRef.current;
    // Find the DataSet. NeoVis usually stores it on the instance or inside network
    const nodesDataset = viz.nodes || (viz._network && viz._network.body && viz._network.body.data.nodes);
    
    if (!nodesDataset) return;

    try {
      const allNodes = nodesDataset.get();
      const updates = allNodes.map(node => {
        // NeoVis stores original neo4j node in node.raw
        const name = node.raw?.properties?.name || node.label;
        if (name && nodeStates[name]) {
           const state = nodeStates[name];
           let color = "#f59e0b"; // attention
           if (state === "compromised") color = "#ff2d55";
           if (state === "fixed") color = "#22ff99";
           return { id: node.id, color };
        }
        return null;
      }).filter(Boolean);
      
      if (updates.length > 0) {
        nodesDataset.update(updates);
      }
    } catch (e) {
      console.warn("Failed to update node colors dynamically", e);
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

      <div className="graph-area">
        {loading && (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            color: "var(--text-secondary)", fontFamily: "JetBrains Mono, monospace",
            fontSize: "12px", zIndex: 5,
          }}>
            Connecting to Neo4j...
          </div>
        )}
        {error && (
          <div style={{
            position: "absolute", inset: 0, display: "flex",
            alignItems: "center", justifyContent: "center",
            color: "var(--red)", fontFamily: "JetBrains Mono, monospace",
            fontSize: "12px", zIndex: 5, flexDirection: "column", gap: "8px",
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