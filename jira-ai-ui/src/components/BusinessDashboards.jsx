import { useEffect, useState } from "react";
import KpiCard from "./KpiCard";

export default function BusinessDashboard() {
  const [summary, setSummary] = useState(null);
  const [ticketTypes, setTicketTypes] = useState([]);

  const [ticket, setTicket] = useState("");
  const [executorComments, setExecutorComments] = useState(null);
  const [loadingComment, setLoadingComment] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/business/summary")
      .then((r) => r.json())
      .then(setSummary);

    fetch("http://localhost:8000/business/ticket-type")
      .then((r) => r.json())
      .then(setTicketTypes);
  }, []);

  const fetchFinalComment = () => {
    if (!ticket) return;

    setLoadingComment(true);
    setExecutorComments(null);

    fetch(`http://localhost:8000/business/ticket/${ticket}/comments`)
      .then((r) => r.json())
      .then((data) => {
        setExecutorComments(data.executor_comments || []);
      })
      .catch(() => {
        setExecutorComments([]);
      })
      .finally(() => setLoadingComment(false));
  };

  if (!summary) return <p style={{ textAlign: "center" }}>Loading…</p>;

  return (
    <div style={container}>
      <h1>📊 Jira AI – Business Overview</h1>

      {/* KPI CARDS */}
      <div style={kpiRow}>
        <KpiCard title="Total Tickets" value={summary.total_tickets} color="#3b82f6" />
        <KpiCard title="Unknown Intent" value={summary.unknown_intent} color="#ef4444" />
        <KpiCard title="SOP Completed" value={summary.sop_completed} color="#22c55e" />
        <KpiCard title="SOP Stopped" value={summary.sop_stopped} color="#f97316" />
      </div>

      {/* FINAL COMMENT LOOKUP */}
      <h2>📝 Ticket Executor Comments</h2>

      <div style={inputRow}>
        <input
          value={ticket}
          onChange={(e) => setTicket(e.target.value)}
          placeholder="LOGFTC-36181"
          style={input}
        />
        <button onClick={fetchFinalComment} style={button}>
          Fetch
        </button>
      </div>

      {loadingComment && <p>Loading comments…</p>}

      {/* EXECUTOR COMMENTS */}
      {executorComments && (
        <div style={{ width: "100%", maxWidth: 800 }}>
          {executorComments.length === 0 && (
            <p style={{ opacity: 0.7 }}>No executor comments available.</p>
          )}

          {executorComments.map((block, idx) => (
            <div key={idx} style={executorCard}>
              <div style={executorHeader(block.executor)}>
                👤 {block.executor}
              </div>

              <ul style={commentList}>
                {block.comments.map((c, i) => (
                  <li key={i} style={commentItem}>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* SOP DISTRIBUTION */}
      <h2>📂 Ticket Type Distribution</h2>

      <div style={tableWrapper}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
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

const kpiRow = {
  display: "flex",
  gap: 16,
  justifyContent: "center",
  flexWrap: "wrap",
  marginBottom: 40,
};

const inputRow = {
  display: "flex",
  justifyContent: "center",
  gap: 10,
  marginBottom: 24,
};

const input = {
  padding: 10,
  borderRadius: 8,
  border: "none",
  width: 220,
};

const button = {
  padding: "10px 16px",
  borderRadius: 8,
  border: "none",
  background: "#2563eb",
  color: "white",
  cursor: "pointer",
};

const executorCard = {
  background: "#0f172a",
  borderRadius: 12,
  padding: 16,
  marginBottom: 16,
  textAlign: "left",
};

const executorHeader = (executor) => ({
  fontWeight: 600,
  marginBottom: 10,
  color:
    executor === "INFO"
      ? "#38bdf8"
      : executor === "THREE_PL"
      ? "#facc15"
      : "#f87171",
});

const commentList = {
  paddingLeft: 20,
};

const commentItem = {
  marginBottom: 6,
};

const tableWrapper = {
  marginTop: 12,
  background: "#020617",
  borderRadius: 12,
  overflow: "hidden",
  maxWidth: 600,
  marginInline: "auto",
};

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
