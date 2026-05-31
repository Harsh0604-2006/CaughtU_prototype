const navItems = [
  { name: "Dashboard", icon: "◇" },
  { name: "Blue Agent", icon: "◆" },
  { name: "Red Agent", icon: "▲" },
  { name: "Database", icon: "⬢" },
  { name: "Logs", icon: "▣" },
];

export default function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
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
    </aside>
  );
}