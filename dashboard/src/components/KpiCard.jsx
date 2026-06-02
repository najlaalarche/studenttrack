export default function KpiCard({ label, value, color = "#6366F1", sub, icon }) {
  return (
    <div style={{
      backgroundColor: "#16161F",
      border: "1px solid #1E1E2E",
      borderRadius: 8,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 6,
      boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748B" }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: 16, opacity: 0.6 }}>{icon}</span>}
      </div>
      <span style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1.1 }}>
        {value ?? "—"}
      </span>
      {sub && <span style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{sub}</span>}
    </div>
  );
}
