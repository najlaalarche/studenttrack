export default function StatutBadge({ statut, size = "sm" }) {
  const map = {
    AUTORISE: { bg: "rgba(141,198,63,0.12)",  border: "rgba(141,198,63,0.4)",  color: "#5a9e14", label: "AUTORISÉ" },
    AVERTI:   { bg: "rgba(245,158,11,0.12)",  border: "rgba(245,158,11,0.4)",  color: "#d97706", label: "AVERTI"   },
    EXCLU:    { bg: "rgba(239,68,68,0.12)",   border: "rgba(239,68,68,0.35)",  color: "#dc2626", label: "EXCLU"    },
  };
  const s = map[statut] ?? { bg: "rgba(100,116,139,0.1)", border: "rgba(100,116,139,0.3)", color: "#64748b", label: statut ?? "—" };
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
      fontWeight: 700,
      letterSpacing: "0.04em",
      display: "inline-block",
      whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  );
}
