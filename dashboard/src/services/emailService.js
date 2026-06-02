import emailjs from '@emailjs/browser'

emailjs.init(import.meta.env.VITE_EMAILJS_PUBLIC_KEY)

const SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID

const TEMPLATES = {
  etudiant_20:    import.meta.env.VITE_TPL_ETUDIANT_20,
  etudiant_30:    import.meta.env.VITE_TPL_ETUDIANT_30,
  etudiant_50:    import.meta.env.VITE_TPL_ETUDIANT_50,
  chef_30:        import.meta.env.VITE_TPL_CHEF_30,
  chef_50:        import.meta.env.VITE_TPL_CHEF_50,
  direction_50:   import.meta.env.VITE_TPL_DIRECTION_50,
}

// Anti-doublon localStorage — 1 email max par seuil par étudiant par module
function alreadySent(studentId, module, seuil) {
  return !!localStorage.getItem(`st_alert_${studentId}_${module}_${seuil}`)
}
function markSent(studentId, module, seuil) {
  localStorage.setItem(`st_alert_${studentId}_${module}_${seuil}`, Date.now())
}

// Envoi unique
export async function sendAlert({ etudiant, module, taux, seuil, destinataire, toEmail }) {
  const key = `${destinataire}_${seuil}`

  if (alreadySent(etudiant.id, module, seuil)) return { sent: false, reason: 'doublon' }
  if (!TEMPLATES[key]) return { sent: false, reason: 'template_manquant' }

  const params = {
    to_email:      toEmail,
    to_name:       `${etudiant.prenom} ${etudiant.nom}`,
    student_name:  `${etudiant.prenom} ${etudiant.nom}`,
    student_id:    etudiant.id,
    filiere:       etudiant.filiere,
    module_name:   module,
    taux_absence:  `${taux}%`,
    seuil:         `${seuil}%`,
    score_global:  etudiant.score_global,
    date_alerte:   new Date().toLocaleDateString('fr-FR'),
  }

  try {
    await emailjs.send(SERVICE_ID, TEMPLATES[key], params)
    markSent(etudiant.id, module, seuil)
    return { sent: true }
  } catch (err) {
    return { sent: false, reason: 'erreur_envoi', err }
  }
}

// Appelé pour chaque étudiant après fetch /api/alertes
export async function processAlerts(etudiant, contacts) {
  for (const m of etudiant.modules_en_alerte || []) {

    if (m.taux_nj >= 20)
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_nj,
        seuil: 20, destinataire: 'etudiant', toEmail: contacts.etudiant_email })

    if (m.taux_nj >= 30) {
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_nj,
        seuil: 30, destinataire: 'etudiant', toEmail: contacts.etudiant_email })
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_nj,
        seuil: 30, destinataire: 'chef', toEmail: contacts.chef_email })
    }

    if (m.taux_total >= 50) {
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_total,
        seuil: 50, destinataire: 'etudiant', toEmail: contacts.etudiant_email })
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_total,
        seuil: 50, destinataire: 'chef', toEmail: contacts.chef_email })
      await sendAlert({ etudiant, module: m.nom, taux: m.taux_total,
        seuil: 50, destinataire: 'direction', toEmail: contacts.direction_email })
    }
  }
}
