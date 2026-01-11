import { useState } from "react";

export default function DevDashboard() {
  const [ticket, setTicket] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchTicket = () => {
    if (!ticket) return;

    setLoading(true);
    setData(null);

    fetch(`http://localhost:8000/dev/ticket/${ticket}`)
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  };

  return (
    <div style={container}>
      <h1>🧑‍💻 Developer Console</h1>

      {/* REPORT DOWNLOADS */}
      <section style={section}>
        <h2>📥 Reports</h2>

        <div style={buttonRow}>
          <a href="http://localhost:8000/dev/reports/business">
            <button style={btnSecondary}>⬇️ Business Report</button>
          </a>

          <a href="http://localhost:8000/dev/reports/unknown">
            <button style={btnDanger}>⚠️ Unknown Intent</button>
          </a>

          <a href="http://localhost:8000/dev/reports/daily">
            <button style={btnSecondary}>📄 Daily Failures</button>
          </a>
        </div>
      </section>

      {/* TICKET DEBUG */}
      <section style={section}>
        <h2>🔍 Ticket Debug</h2>

        <div style={inputRow}>
          <input
            value={ticket}
            onChange={(e) => setTicket(e.target.value)}
            placeholder="LOGFTC-36181"
            style={input}
          />
          <button onClick={fetchTicket} style={btnPrimary}>
            Fetch
          </button>
        </div>

        {loading && <p style={{ opacity: 0.7 }}>Fetching ticket data…</p>}
      </section>

      {/* RAW JSON OUTPUT */}
      {data && (
        <section style={section}>
          <h2>🧾 Raw Execution Data</h2>

          <pre style={jsonBox}>
            {JSON.stringify(data, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

/* ===================== STYLES ===================== */

const container = {
  maxWidth: 1000,
  margin: "0 auto",
  padding: 24,
  textAlign: "center",
};

const section = {
  marginTop: 32,
};

const buttonRow = {
  display: "flex",
  justifyContent: "center",
  gap: 12,
  flexWrap: "wrap",
  marginTop: 12,
};

const inputRow = {
  display: "flex",
  justifyContent: "center",
  gap: 10,
  marginTop: 12,
};

const input = {
  padding: 10,
  borderRadius: 8,
  border: "none",
  width: 240,
};

const btnPrimary = {
  padding: "10px 16px",
  borderRadius: 8,
  border: "none",
  background: "#3b82f6",
  color: "white",
  cursor: "pointer",
};

const btnSecondary = {
  padding: "10px 14px",
  borderRadius: 8,
  border: "none",
  background: "#334155",
  color: "white",
  cursor: "pointer",
};

const btnDanger = {
  padding: "10px 14px",
  borderRadius: 8,
  border: "none",
  background: "#ef4444",
  color: "white",
  cursor: "pointer",
};

const jsonBox = {
  background: "#020617",
  padding: 16,
  borderRadius: 12,
  maxHeight: 450,
  overflow: "auto",
  fontSize: 13,
  textAlign: "left",
  marginTop: 12,
};
