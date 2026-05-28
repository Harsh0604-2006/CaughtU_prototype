const navItems = [
  { name: "Dashboard", icon: "◇" },
  { name: "Blue Agent", icon: "◆" },
  { name: "Red Agent", icon: "▲" },
  { name: "Database", icon: "⬢" },
  { name: "Logs", icon: "▣" },
  { name: "Settings", icon: "⚙" },
];

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">CD</div>

        <div>
          <p className="brand-title">Cyber</p>
          <p className="brand-subtitle">Defense OS</p>
        </div>
      </div>

      <nav className="nav-list">
        {navItems.map((item) => (
          <button
            key={item.name}
            type="button"
            className={`nav-item ${active === item.name ? "active" : ""}`}
            onClick={() => onNavigate(item.name)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.name}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="signal-dot"></span>
        <span>Secure Link Active</span>
      </div>
    </aside>
  );
}