// Carte performance du portail étudiant :
// Moyenne brute | Moyenne nette | Taux de performance perdu, puis slider 0 → 100 % du taux

const VERT   = "#22c55e";
const ORANGE = "#f97316";
const ROUGE  = "#ef4444";

const fmt     = v => (v === null || v === undefined ? "—" : Number(v).toFixed(2));
const ordinal = r => (r === 1 ? "1er" : `${r}ème`);

// 0–5 % vert 😊 · 5–15 % orange 😐 · > 15 % rouge 😟
function niveau(taux) {
  if (taux < 5)   return { couleur: VERT,   emoji: "😊" };
  if (taux <= 15) return { couleur: ORANGE, emoji: "😐" };
  return            { couleur: ROUGE,  emoji: "😟" };
}

const SEUILS = [5, 15];

const CARD  = { backgroundColor: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: 8, padding: "20px 28px", marginBottom: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const LABEL = { fontSize: 11, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "#64748b" };
const GRAND = { fontSize: "2.25rem", fontWeight: 700, lineHeight: 1.1, margin: "6px 0 8px" };

function Badge({ rang, effectif, couleur }) {
  if (!rang) return <span style={{ fontSize: 12, color: "#94a3b8" }}>Classement —</span>;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "3px 10px", borderRadius: 999, fontSize: 12, fontWeight: 600,
      color: couleur, backgroundColor: `${couleur}14`, border: `1px solid ${couleur}40`,
    }}>
      🏅 {ordinal(rang)} / {effectif}
    </span>
  );
}

function Colonne({ label, children }) {
  return (
    <div style={{ textAlign: "center", minWidth: 0 }}>
      <div style={LABEL}>{label}</div>
      {children}
    </div>
  );
}

function Slider({ taux, couleur, emoji }) {
  const pos = Math.min(Math.max(taux, 0), 100);
  return (
    <div style={{ padding: "18px 14px 0" }}>
      <div
        role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={taux}
        aria-label="Performance perdue à cause des absences"
        style={{ position: "relative", height: 12, borderRadius: 99, backgroundColor: "#F1F5F9" }}
      >
        <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${pos}%`, backgroundColor: couleur, borderRadius: 99 }} />
        {SEUILS.map(p => (
          <div key={p} aria-hidden="true" style={{ position: "absolute", left: `${p}%`, top: -4, height: 20, width: 2, marginLeft: -1, backgroundColor: "#94a3b8", borderRadius: 1 }} />
        ))}
        {/* emoji centré sur la barre, à la position exacte du taux */}
        <div aria-hidden="true" style={{
          position: "absolute", left: `${pos}%`, top: "50%", transform: "translate(-50%, -50%)",
          width: 34, height: 34, borderRadius: "50%", backgroundColor: "#FFFFFF",
          border: `2px solid ${couleur}`, boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, lineHeight: 1, zIndex: 2,
        }}>
          {emoji}
        </div>
      </div>
      <div aria-hidden="true" style={{ position: "relative", height: 16, marginTop: 14, fontSize: 10, color: "#64748b" }}>
        <span style={{ position: "absolute", left: 0, transform: "translateX(-50%)" }}>0%</span>
        {SEUILS.map(p => (
          <span key={p} style={{ position: "absolute", left: `${p}%`, transform: "translateX(-50%)", fontWeight: 600 }}>{p}%</span>
        ))}
        <span style={{ position: "absolute", left: "100%", transform: "translateX(-50%)" }}>100%</span>
      </div>
    </div>
  );
}

// perf : réponse de GET /api/etudiant/<id>/performance, ou null si aucune moyenne importée
export default function PerformanceTile({ perf }) {
  if (!perf) {
    return (
      <div style={CARD}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b", marginBottom: 6 }}>Performance</div>
        <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>Moyennes brute et nette pas encore disponibles.</p>
      </div>
    );
  }

  const taux = perf.taux_performance_perdue;
  const n    = taux === null ? null : niveau(taux);

  return (
    <div style={CARD}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#1a3a6b" }}>Performance</div>
        {perf.annee_scolaire && <div style={{ fontSize: 11, color: "#94a3b8" }}>{perf.annee_scolaire}</div>}
      </div>

      {/* 1. Moyenne brute | Moyenne nette | Taux de performance */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr 1fr", gap: 16, alignItems: "start" }}>
        <Colonne label="Moyenne brute">
          <div style={{ ...GRAND, color: "#1e293b" }}>
            {fmt(perf.moyenne_brute)}<span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 500 }}>/20</span>
          </div>
          <Badge rang={perf.classement_brut} effectif={perf.effectif_brut} couleur={ORANGE} />
        </Colonne>

        <Colonne label="Moyenne nette">
          <div style={{ ...GRAND, color: n ? n.couleur : "#1e293b" }}>
            {fmt(perf.moyenne_nette)}<span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 500 }}>/20</span>
          </div>
          <Badge rang={perf.classement_net} effectif={perf.effectif_net} couleur={ROUGE} />
        </Colonne>

        <Colonne label="Taux de performance">
          <div style={{ ...GRAND, fontSize: "2.75rem", color: ROUGE }}>
            {taux === null ? "—" : `${taux.toFixed(1)}%`}
          </div>
          <div style={{ fontSize: 13, color: "#64748b" }}>perdu à cause des absences</div>
        </Colonne>
      </div>

      {/* 2. Slider */}
      {n && (
        <div style={{ marginTop: 20, paddingTop: 8, borderTop: "1px solid #F1F5F9" }}>
          <Slider taux={taux} couleur={n.couleur} emoji={n.emoji} />
        </div>
      )}
    </div>
  );
}
