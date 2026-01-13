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

  const fetchFinalComment = () => {
    if (!ticket) return;

    setLoadingComment(true);
    setFinalComment(null);

    fetch(`http://localhost:8000/business/ticket/${ticket}/comments`)
      .then((r) => r.json())
      .then((data) => {
        if (!data || !data.executor_comments?.length) {
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

  if (!summary) return <p style={{ textAlign: "center" }}>Loading…</p>;

  return (
    <div style={container}>
      <h1 style={{ marginBottom: 24 }}>📊 Jira AI – Business Overview</h1>

      {/* KPI CARDS */}
      <div style={kpiRow}>
        <KpiCard title="Total Tickets" value={summary.total_tickets} color="#3b82f6" />
        <KpiCard title="Unknown Intent" value={summary.unknown_intent} color="#ef4444" />
        <KpiCard title="SOP Completed" value={summary.sop_completed} color="#22c55e" />
        <KpiCard title="SOP Stopped" value={summary.sop_stopped} color="#f97316" />
      </div>

      {/* FINAL COMMENT LOOKUP */}
      <section style={section}>
        <h2>📝 Ticket Execution Summary</h2>

        <div style={inputRow}>
          <input
            value={ticket}
            onChange={(e) => setTicket(e.target.value)}
            placeholder="LOGFTC-36181"
            style={input}
          />
          <button onClick={fetchFinalComment} style={btnPrimary}>
            View
          </button>
        </div>

        {loadingComment && <p style={{ opacity: 0.7 }}>Loading comment…</p>}

        {finalComment && (
          <div style={commentBox}>
            {typeof finalComment === "string" ? (
              finalComment
            ) : (
              finalComment.map((block, i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <strong>{block.executor}</strong>
                  <ul>
                    {block.comments.map((c, j) => (
                      <li key={j}>{c}</li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>
        )}
      </section>

      {/* SOP DISTRIBUTION */}
      <section style={section}>
        <h2>📂 Ticket Type Distribution</h2>

        <div style={tableWrapper}>
          <table style={table}>
            <thead>
              <tr style={{ background: "#020617" }}>
                <th style={{ ...th, width: "70%" }}>SOP</th>
                <th style={{ ...th, width: "30%", textAlign: "right" }}>
                  Tickets
                </th>
              </tr>
            </thead>
            <tbody>
              {ticketTypes.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ ...td, width: "70%" }}>
                    {typeof row._id === "string"
                      ? row._id
                      : row._id?.sop || "UNKNOWN"}
                  </td>
                  <td
                    style={{
                      ...td,
                      width: "30%",
                      textAlign: "right",
                      fontWeight: 600,
                    }}
                  >
                    {row.count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

/* ===================== STYLES ===================== */

const container = {
  maxWidth: 1100,
  margin: "0 auto",
  padding: 24,
  textAlign: "center",
};

const section = {
  marginTop: 40,
};

const kpiRow = {
  display: "flex",
  gap: 16,
  justifyContent: "center",
  flexWrap: "wrap",
};

const inputRow = {
  display: "flex",
  justifyContent: "center",
  gap: 10,
  marginTop: 16,
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
  background: "#2563eb",
  color: "white",
  cursor: "pointer",
};

const commentBox = {
  marginTop: 20,
  background: "#0f172a",
  padding: 16,
  borderRadius: 12,
  maxWidth: 900,
  marginLeft: "auto",
  marginRight: "auto",
  textAlign: "left",
  fontSize: 14,
};

const tableWrapper = {
  marginTop: 16,
  background: "var(--card)",
  borderRadius: 12,
  overflow: "hidden",
  maxWidth: 700,
  marginLeft: "auto",
  marginRight: "auto",
};

const table = {
  width: "100%",
  borderCollapse: "collapse",
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
  verticalAlign: "top",
  whiteSpace: "normal",
};
