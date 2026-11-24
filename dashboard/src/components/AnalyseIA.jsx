import { useState } from "react";
import { postAnalyseIA } from "../api.js";

const MSG_INDISPONIBLE = "Le service d'analyse IA n'est pas disponible pour le moment.";

// État partagé entre le bouton et la carte (placés à des endroits différents de la page)
export function useAnalyseIA(role) {
  const [etat, setEtat] = useState({ loading: false, analyse: null, erreur: null });

  async function lancer(data) {
    setEtat({ loading: true, analyse: null, erreur: null });
    try {
      const res = await postAnalyseIA(role, data);
      setEtat(res?.analyse
        ? { loading: false, analyse: res.analyse, erreur: null }
        : { loading: false, analyse: null, erreur: res?.erreur || MSG_INDISPONIBLE });
    } catch {
      setEtat({ loading: false, analyse: null, erreur: MSG_INDISPONIBLE });
    }
  }

  return { ...etat, lancer, fermer: () => setEtat({ loading: false, analyse: null, erreur: null }) };
}

export function BoutonAnalyseIA({ ia, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={ia.loading}
      className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors ${
        ia.loading ? "cursor-not-allowed bg-gray-400" : "bg-[#1e3a5f] hover:bg-[#16304f]"
      }`}
    >
      ✨ Analyser avec l'IA
    </button>
  );
}

export function CarteAnalyseIA({ ia }) {
  if (!ia.loading && !ia.analyse && !ia.erreur) return null;
  return (
    <div className="relative mb-6 flex gap-3 rounded-lg border-l-4 border-[#1e3a5f] bg-[#f0f7ff] px-5 py-4 shadow-sm">
      <span className="text-xl leading-none" aria-hidden="true">🤖</span>
      <div className="min-w-0 flex-1 pr-6">
        {ia.loading ? (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-[#1e3a5f]" />
            Analyse en cours...
          </div>
        ) : ia.erreur ? (
          <p className="text-sm text-[#b45309]">{ia.erreur}</p>
        ) : (
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-700">{ia.analyse}</p>
        )}
      </div>
      {!ia.loading && (
        <button
          onClick={ia.fermer}
          aria-label="Fermer l'analyse"
          className="absolute right-3 top-2 text-lg leading-none text-gray-400 hover:text-gray-600"
        >×</button>
      )}
    </div>
  );
}
