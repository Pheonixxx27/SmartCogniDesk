import { useEffect, useState } from "react";
import KpiCard from "./KpiCard";

export default function BusinessDashboard() {
  const [summary, setSummary] = useState(null);
  const [ticketTypes, setTicketTypes] = useState([]);

  const [ticket, setTicket] = useState("");
  const [finalComment, setFinalComment] = useState(null);
  const [loadingComment, setLoadingComment] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/business/summary")
      .then((r) => r.json())
      .then(setSummary);

    fetch("http://localhost:8000/business/ticket-type")
      .then((r) => r.json())
      .then(setTicketTypes);
  }, []);

  // ✅ FIXED: use business-safe endpoint
  const fetchFinalComment = () => {
    if (!ticket) return;

    setLoadingComment(true);
    setFinalComment(null);

    fetch(`http://localhost:8000/business/ticket/${ticket}/comments`)
      .then((r) => r.json())
      .then((data) => {
        if (!data || !data.executor_comments) {
          setFinalComment("No final comment generated for this ticket.");
          return;
        }

        setFinalComment(data.executor_comments);
      })
      .catch(() => {
        setFinalComment("Unable to fetch final comment.");
      })
      .finally(() => setLoadingComment(false));
  };

  if (!summary) return <p>Loading...</p>;

  return (
    <>
      <h1 style={{ marginBottom: 20 }}>📊 Jira AI – Business Overview</h1>

      {/* KPI CARDS */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <KpiCard title="Total Tickets" value={summary.total_tickets} color="#3b82f6" />
        <KpiCard title="Unknown Intent" value={summary.unknown_intent} color="#ef4444" />
        <KpiCard title="SOP Completed" value={summary.sop_completed} color="#22c55e" />
        <KpiCard title="SOP Stopped" value={summary.sop_stopped} color="#f97316" />
      </div>

      {/* FINAL COMMENT LOOKUP */}
      <h2 style={{ marginTop: 40 }}>📝 Ticket Final Comment</h2>

      <div style={{ marginTop: 10, marginBottom: 20 }}>
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
          onClick={fetchFinalComment}
          style={{
            padding: "10px 16px",
            borderRadius: 8,
            border: "none",
            background: "#2563eb",
            color: "white",
            cursor: "pointer",
          }}
        >
          View Comment
        </button>
      </div>

      {loadingComment && <p>Loading comment…</p>}

      {finalComment && (
        <div
          style={{
            background: "#0f172a",
            padding: 16,
            borderRadius: 12,
            maxWidth: 800,
            fontSize: 14,
            whiteSpace: "pre-wrap",
          }}
        >
          {finalComment}
        </div>
      )}

      {/* SOP DISTRIBUTION */}
      <h2 style={{ marginTop: 40 }}>📂 Ticket Type Distribution</h2>

      <div
        style={{
          marginTop: 12,
          background: "var(--card)",
          borderRadius: 12,
          overflow: "hidden",
          maxWidth: 600,
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#020617" }}>
              <th style={th}>SOP Name</th>
              <th style={th}>Ticket Count</th>
            </tr>
          </thead>
          <tbody>
            {ticketTypes.map((row) => (
              <tr key={row._id}>
                <td style={td}>{row._id}</td>
                <td style={td}>{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

const th = {
  textAlign: "left",
  padding: 12,
  fontSize: 14,
  color: "#9ca3af",
};

const td = {
  padding: 12,
  borderTop: "1px solid #1f2933",
};
