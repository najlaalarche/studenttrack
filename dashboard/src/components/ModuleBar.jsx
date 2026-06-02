export default function ModuleBar({ taux_nj = 0, taux_total = 0, seuil_alerte = 20, seuil_exclusion = 50 }) {
  const clamp = (v) => Math.min(Math.max(v, 0), 100);
  const njW    = clamp(taux_nj);
  const totalW = clamp(taux_total);
  const extraW = clamp(totalW - njW);

  return (
    <div style={{ width: "100%" }}>
      {/* Barre principale */}
      <div style={{ position: "relative", height: 8, borderRadius: 99, backgroundColor: "#1E1E2E", overflow: "visible" }}>
        {/* Fill NJ - gradient orange */}
        {njW > 0 && (
          <div style={{
            position: "absolute", left: 0, top: 0, height: "100%", width: `${njW}%`,
            background: "linear-gradient(90deg, #F97316, #FB923C)",
            borderRadius: 99,
            transition: "width 0.4s ease",
          }} />
        )}
        {/* Fill total supplémentaire - rouge */}
        {extraW > 0 && (
          <div style={{
            position: "absolute", top: 0, height: "100%",
            left: `${njW}%`, width: `${extraW}%`,
            background: "linear-gradient(90deg, #EF4444, #F87171)",
            borderRadius: "0 99px 99px 0",
            transition: "all 0.4s ease",
          }} />
        )}
        {/* Marqueur 20% */}
        <div style={{
          position: "absolute", top: -3, height: 14, width: 1.5,
          left: `${seuil_alerte}%`,
          backgroundColor: "#F97316",
          opacity: 0.8,
          zIndex: 2,
        }} />
        {/* Marqueur 50% */}
        <div style={{
          position: "absolute", top: -3, height: 14, width: 1.5,
          left: `${seuil_exclusion}%`,
          backgroundColor: "#EF4444",
          opacity: 0.8,
          zIndex: 2,
        }} />
      </div>

      {/* Labels */}
      <div style={{ position: "relative", marginTop: 8, height: 14 }}>
        <span style={{ position: "absolute", left: 0, fontSize: 10, color: "#64748B" }}>0%</span>
        <span style={{ position: "absolute", left: `${seuil_alerte}%`, transform: "translateX(-50%)", fontSize: 10, color: "#F97316", fontWeight: 500 }}>
          {seuil_alerte}%
        </span>
        <span style={{ position: "absolute", left: `${seuil_exclusion}%`, transform: "translateX(-50%)", fontSize: 10, color: "#EF4444", fontWeight: 500 }}>
          {seuil_exclusion}%
        </span>
        <span style={{ position: "absolute", right: 0, fontSize: 10, color: "#64748B" }}>100%</span>
      </div>
    </div>
  );
}
