import { useEffect, useState } from "react";

export default function DevDashboard() {
  const [ticket, setTicket] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const [asnReports, setAsnReports] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/dev/reports/asn-do")
      .then((r) => r.json())
      .then(setAsnReports);
  }, []);

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

        <div style={row}>
          <a href="http://localhost:8000/dev/reports/business">
            <button style={btnSecondary}>Business</button>
          </a>
          <a href="http://localhost:8000/dev/reports/unknown">
            <button style={btnDanger}>Unknown</button>
          </a>
          <a href="http://localhost:8000/dev/reports/daily">
            <button style={btnSecondary}>Daily</button>
          </a>
        </div>
      </section>

      {/* ASN / DO REPORTS */}
      <section style={section}>
        <h2>🚚 ASN / DO Failed Executions</h2>

        {asnReports.length === 0 && (
          <p style={{ opacity: 0.6 }}>No ASN / DO failures detected 🎉</p>
        )}

        {asnReports.map((r) => (
          <div key={r.file} style={card}>
            <strong>{r.ticket}</strong>
            <p>{r.file}</p>
            <a href={`http://localhost:8000${r.download_url}`}>
              ⬇️ Download Excel
            </a>
          </div>
        ))}
      </section>

      {/* TICKET DEBUG */}
      <section style={section}>
        <h2>🔍 Ticket Debug</h2>

        <div style={row}>
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

        {loading && <p>Fetching ticket data…</p>}
      </section>

      {data && (
        <pre style={jsonBox}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

/* ===================== STYLES ===================== */

const container = {
  maxWidth: 1000,
  margin: "0 auto",
  padding: 24,
};

const section = { marginTop: 32 };

const row = {
  display: "flex",
  gap: 12,
  flexWrap: "wrap",
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
};

const btnSecondary = {
  padding: "10px 14px",
  borderRadius: 8,
  border: "none",
  background: "#334155",
  color: "white",
};

const btnDanger = {
  padding: "10px 14px",
  borderRadius: 8,
  border: "none",
  background: "#ef4444",
  color: "white",
};

const card = {
  background: "#020617",
  padding: 16,
  borderRadius: 12,
  marginTop: 12,
};

const jsonBox = {
  background: "#020617",
  padding: 16,
  borderRadius: 12,
  maxHeight: 450,
  overflow: "auto",
  fontSize: 13,
  marginTop: 12,
};
