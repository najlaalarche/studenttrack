const S = {
  th: { padding: "10px 16px", fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b", textAlign: "left", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" },
  td: { padding: "11px 16px", fontSize: 13, borderBottom: "1px solid #E2E8F0", color: "#1e293b" },
};

export const fmtMoyenne = (m) => `${Number(Number(m).toFixed(2))}/20`;

// Props pour KpiCard : "12.8/20" + "Validé ✓" (vert) ou "Non validé ✗" (rouge), "—" sans notes
export function moyenneKpi(moyenne) {
  if (moyenne == null) return { value: "—", color: "#1a3a6b" };
  const valide = moyenne >= 10;
  return {
    value: fmtMoyenne(moyenne),
    sub:   valide ? "Validé ✓" : "Non validé ✗",
    color: valide ? "#5a9e14" : "#dc2626",
  };
}

export default function NotesTable({ notes = [] }) {
  return (
    <div style={{ backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, overflow: "auto", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr>{["Semestre", "Moyenne", "Statut", "Année scolaire"].map(h => <th key={h} style={S.th}>{h}</th>)}</tr></thead>
        <tbody>
          {notes.length === 0
            ? <tr><td colSpan={4} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>Aucune note</td></tr>
            : notes.map((n, i) => {
              const valide = n.moyenne_generale >= 10;
              return (
                <tr key={`${n.annee_universitaire}-${n.semestre}`} style={{ backgroundColor: i % 2 === 0 ? "#FFFFFF" : "#F8FAFC" }}>
                  <td style={{ ...S.td, fontWeight: 600 }}>{n.semestre || "—"}</td>
                  <td style={{ ...S.td, fontWeight: 700, color: valide ? "#5a9e14" : "#dc2626" }}>{fmtMoyenne(n.moyenne_generale)}</td>
                  <td style={S.td}><span style={{ color: valide ? "#5a9e14" : "#dc2626", fontSize: 12, fontWeight: 600 }}>{valide ? "Validé ✓" : "Non validé ✗"}</span></td>
                  <td style={{ ...S.td, color: "#64748b" }}>{n.annee_universitaire}</td>
                </tr>
              );
            })
          }
        </tbody>
      </table>
    </div>
  );
}
