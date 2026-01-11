import { useState } from "react";

export default function DevDashboard() {
  const [ticket, setTicket] = useState("");
  const [data, setData] = useState(null);

  const fetchTicket = () => {
    fetch(`http://localhost:8000/dev/ticket/${ticket}`)
      .then((r) => r.json())
      .then(setData);
  };

  return (
    <>
      <h1>🧑‍💻 Developer Console</h1>

      {/* REPORT DOWNLOADS */}
      <div style={{ marginBottom: 20 }}>
        <a href="http://localhost:8000/dev/reports/business">
          <button style={btnSecondary}>⬇️ Business Report</button>
        </a>

        <a
          href="http://localhost:8000/dev/reports/unknown"
          style={{ marginLeft: 10 }}
        >
          <button style={btnDanger}>⚠️ Unknown Intent</button>
        </a>

        <a
          href="http://localhost:8000/dev/reports/daily"
          style={{ marginLeft: 10 }}
        >
          <button style={btnSecondary}>📄 Daily Failures</button>
        </a>
      </div>

      {/* TICKET DEBUG */}
      <div style={{ marginBottom: 20 }}>
        <input
          value={ticket}
          onChange={(e) => setTicket(e.target.value)}
          placeholder="LOGFTC-12345"
          style={{
            padding: 10,
            borderRadius: 8,
            border: "none",
            width: 220,
            marginRight: 10,
          }}
        />
        <button
          onClick={fetchTicket}
          style={{
            padding: "10px 16px",
            borderRadius: 8,
            border: "none",
            background: "#3b82f6",
            color: "white",
            cursor: "pointer",
          }}
        >
          Fetch
        </button>
      </div>

      {data && (
        <pre
          style={{
            background: "#020617",
            padding: 16,
            borderRadius: 10,
            maxHeight: 400,
            overflow: "auto",
            fontSize: 13,
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </>
  );
}

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
