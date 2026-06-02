export default function KpiCard({ label, value, color = "#1a3a6b", sub, icon }) {
  return (
    <div style={{
      backgroundColor: "#FFFFFF",
      border: "1px solid #E2E8F0",
      borderLeft: `4px solid ${color}`,
      borderRadius: 8,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 6,
      boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b" }}>
          {label}
        </span>
        {icon && <span style={{ fontSize: 16, opacity: 0.4 }}>{icon}</span>}
      </div>
      <span style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1.1 }}>
        {value ?? "—"}
      </span>
      {sub && <span style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>{sub}</span>}
    </div>
  );
}
