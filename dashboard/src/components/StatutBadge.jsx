export default function StatutBadge({ statut, size = "sm" }) {
  const map = {
    AUTORISE: { bg: "rgba(34,197,94,0.12)",  border: "rgba(34,197,94,0.3)",  color: "#22C55E", label: "AUTORISÉ" },
    AVERTI:   { bg: "rgba(249,115,22,0.12)", border: "rgba(249,115,22,0.3)", color: "#F97316", label: "AVERTI" },
    EXCLU:    { bg: "rgba(239,68,68,0.12)",  border: "rgba(239,68,68,0.3)",  color: "#EF4444", label: "EXCLU" },
  };
  const s = map[statut] ?? { bg: "rgba(100,116,139,0.12)", border: "rgba(100,116,139,0.3)", color: "#64748B", label: statut ?? "—" };
  const px = size === "lg" ? "10px 14px" : "4px 10px";
  const fs = size === "lg" ? "12px" : "11px";
  return (
    <span style={{
      backgroundColor: s.bg,
      border: `1px solid ${s.border}`,
      color: s.color,
      padding: px,
      borderRadius: 6,
      fontSize: fs,
      fontWeight: 600,
      letterSpacing: "0.04em",
      display: "inline-block",
      whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  );
}
