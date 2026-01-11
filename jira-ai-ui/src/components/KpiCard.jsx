export default function KpiCard({ title, value, color }) {
  return (
    <div
      style={{
        background: "var(--card)",
        padding: 20,
        borderRadius: 12,
        minWidth: 180,
        borderLeft: `6px solid ${color}`,
      }}
    >
      <div style={{ color: "var(--muted)", fontSize: 14 }}>{title}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
