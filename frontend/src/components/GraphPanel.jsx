import { useEffect, useRef, useState } from "react";

// ── Static node layout matching your Neo4j data ──────────────
const NODES = [
  { id:"SRV001", label:"CoreDB",       type:"Server",   x:350, y:160, crit:"critical" },
  { id:"SRV002", label:"AppServer",    type:"Server",   x:210, y:110, crit:"high"     },
  { id:"SRV003", label:"Firewall",     type:"Server",   x:90,  y:160, crit:"critical" },
  { id:"SRV004", label:"Backup",       type:"Server",   x:170, y:255, crit:"medium"   },
  { id:"SRV005", label:"MsgBroker",    type:"Server",   x:310, y:70,  crit:"high"     },
  { id:"SRV006", label:"LoadBalancer", type:"Server",   x:470, y:110, crit:"high"     },
  { id:"SRV007", label:"GenLedger",    type:"Server",   x:490, y:240, crit:"high"     },
  { id:"NET001", label:"IBGateway",    type:"Network",  x:70,  y:70,  crit:"high"     },
  { id:"NET006", label:"APIGateway",   type:"Network",  x:590, y:160, crit:"high"     },
  { id:"API003", label:"PaymentAPI",   type:"API",      x:420, y:285, crit:"critical" },
  { id:"API001", label:"CoreAPI",      type:"API",      x:250, y:285, crit:"high"     },
  { id:"SEC001", label:"IDS/IPS",      type:"Security", x:155, y:185, crit:"critical" },
  { id:"SEC002", label:"UEBA",         type:"Security", x:440, y:185, crit:"critical" },
  { id:"BANK001",label:"SBI Main",     type:"Bank",     x:350, y:290, crit:"critical" },
  { id:"EMP001", label:"Alice",        type:"User",     x:590, y:75,  crit:"low"      },
  { id:"EMP002", label:"Raj",          type:"User",     x:630, y:270, crit:"low"      },
];

const EDGES = [
  ["NET001","SRV003"],["SRV003","SRV002"],["SRV003","SEC001"],
  ["SRV002","SRV001"],["SRV002","SRV005"],["SRV005","SRV001"],
  ["SRV006","SRV002"],["NET006","SRV006"],["NET006","API003"],
  ["SRV001","API001"],["API001","BANK001"],["API003","BANK001"],
  ["SRV001","SRV007"],["SRV007","BANK001"],["SEC002","SRV001"],
  ["SEC002","SRV002"],["EMP001","NET006"],["EMP002","NET006"],
  ["SRV004","SRV001"],
];

const TYPE_COLORS = {
  Server:   "#00d4ff",
  Network:  "#7c6fff",
  API:      "#00ff9d",
  Security: "#ffd60a",
  Bank:     "#ff6b2b",
  User:     "#c8dae8",
};

const NODE_RADIUS = {
  Bank: 22, Server: 16, Security: 14, Network: 13, API: 12, User: 10,
};

export default function GraphPanel({ nodeStates }) {
  const [tooltip, setTooltip] = useState(null);

  const getNodeColor = (node) => {
    const state = nodeStates[node.id];
    if (state === "compromised") return { stroke:"#ff2d55", fill:"rgba(255,45,85,0.15)", glow:"#ff2d55" };
    if (state === "fixed")       return { stroke:"#00ff9d", fill:"rgba(0,255,157,0.1)",  glow:"#00ff9d" };
    return { stroke: TYPE_COLORS[node.type] || "#333", fill:"rgba(8,15,23,0.9)", glow: null };
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.title}>
        <span style={styles.titleBar}/>
        NEO4J NETWORK GRAPH — BANK INFRASTRUCTURE
      </div>

      <svg viewBox="0 0 700 330" style={styles.svg} preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="glow-red">
            <feDropShadow stdDeviation="5" floodColor="#ff2d55" floodOpacity="0.9"/>
          </filter>
          <filter id="glow-green">
            <feDropShadow stdDeviation="5" floodColor="#00ff9d" floodOpacity="0.9"/>
          </filter>
          <filter id="glow-cyan">
            <feDropShadow stdDeviation="3" floodColor="#00d4ff" floodOpacity="0.6"/>
          </filter>
        </defs>

        {/* Edges */}
        {EDGES.map(([a, b], i) => {
          const na = NODES.find(n => n.id === a);
          const nb = NODES.find(n => n.id === b);
          if (!na || !nb) return null;
          const aState = nodeStates[a];
          const bState = nodeStates[b];
          const isHot = aState === "compromised" || bState === "compromised";
          const isDone = aState === "fixed" && bState === "fixed";
          return (
            <line key={i}
              x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
              stroke={isDone ? "rgba(0,255,157,0.3)" : isHot ? "rgba(255,45,85,0.4)" : "#0d2137"}
              strokeWidth={isHot || isDone ? 1.5 : 1}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map(node => {
          const { stroke, fill, glow } = getNodeColor(node);
          const r = NODE_RADIUS[node.type] || 12;
          const state = nodeStates[node.id];
          return (
            <g key={node.id}
              style={{ cursor:"pointer" }}
              onMouseEnter={e => setTooltip({ node, x: e.clientX, y: e.clientY })}
              onMouseLeave={() => setTooltip(null)}
            >
              {/* Outer ring for compromised/fixed */}
              {state && (
                <circle cx={node.x} cy={node.y} r={r + 5}
                  fill="none"
                  stroke={state === "compromised" ? "rgba(255,45,85,0.3)" : "rgba(0,255,157,0.3)"}
                  strokeWidth="1"
                />
              )}
              <circle
                cx={node.x} cy={node.y} r={r}
                fill={fill}
                stroke={stroke}
                strokeWidth={node.crit === "critical" ? 2 : 1}
                filter={glow ? (glow === "#ff2d55" ? "url(#glow-red)" : "url(#glow-green)") : undefined}
                style={{ transition:"all 0.4s" }}
              />
              <text
                x={node.x} y={node.y + r + 12}
                textAnchor="middle"
                fontSize="8"
                fill={state ? stroke : "var(--dim)"}
                fontFamily="Share Tech Mono, monospace"
                style={{ transition:"fill 0.4s" }}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          ...styles.tooltip,
          left: tooltip.x + 12,
          top:  tooltip.y - 10,
        }}>
          {tooltip.node.id} | {tooltip.node.type} | {tooltip.node.crit.toUpperCase()}
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    background:"var(--panel)",
    padding:"16px",
    gridRow:1, gridColumn:1,
    position:"relative",
    overflow:"hidden",
  },
  title: {
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, letterSpacing:3,
    textTransform:"uppercase",
    color:"var(--dim)",
    marginBottom:12,
    display:"flex", alignItems:"center", gap:8,
  },
  titleBar: {
    display:"inline-block",
    width:3, height:12,
    background:"var(--accent)",
  },
  svg: {
    width:"100%",
    height:"calc(100% - 36px)",
  },
  tooltip: {
    position:"fixed",
    background:"var(--panel)",
    border:"1px solid var(--accent)",
    padding:"6px 10px",
    fontFamily:"'Share Tech Mono',monospace",
    fontSize:11, color:"var(--accent)",
    pointerEvents:"none",
    zIndex:100,
  },
};
