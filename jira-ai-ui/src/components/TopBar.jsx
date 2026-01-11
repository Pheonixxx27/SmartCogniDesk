export default function TopBar({ tab, setTab }) {
  const btn = (active) => ({
    padding: "10px 18px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    background: active ? "#3b82f6" : "#1f2933",
    color: "white",
    fontWeight: 600,
  });

  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
      <button style={btn(tab === "business")} onClick={() => setTab("business")}>
        📊 Business
      </button>
      <button style={btn(tab === "dev")} onClick={() => setTab("dev")}>
        🧑‍💻 Dev
      </button>
    </div>
  );
}
