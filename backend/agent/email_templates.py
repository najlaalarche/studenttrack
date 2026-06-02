from datetime import datetime


def _render_header(color: str, title: str, subtitle: str) -> str:
    return (
        f"<tr><td style=\"background:{color};padding:24px 24px 18px 24px;text-align:center;color:#ffffff;\">"
        f"<h1 style=\"margin:0;font-size:22px;font-weight:700;\">StudentTrack — ESITH Casablanca</h1>"
        f"<p style=\"margin:8px 0 0 0;font-size:14px;opacity:0.9;\">{subtitle}</p>"
        f"</td></tr>"
    )


def _render_footer(date_alerte: str) -> str:
    return (
        f"<tr><td style=\"background:#f3f4f6;padding:18px 20px;text-align:center;color:#6b7280;font-size:12px;\">"
        f"Système automatique StudentTrack — {date_alerte} • Ne pas répondre"
        f"</td></tr>"
    )


def _wrap_html(body: str) -> str:
    return (
        "<html><body style=\"margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;\">"
        "<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" role=\"presentation\">"
        "<tr><td align=\"center\" style=\"padding:20px;\">"
        "<table width=\"600\" cellpadding=\"0\" cellspacing=\"0\" role=\"presentation\" style=\"background:#ffffff;border-radius:10px;overflow:hidden;\">"
        f"{body}"
        "</table></td></tr></table></body></html>"
    )


def _bold_row(label: str, value: str) -> str:
    return (
        f"<tr><td style=\"padding:6px 0;color:#4b5563;font-size:14px;vertical-align:top;\">{label}</td>"
        f"<td style=\"padding:6px 0;color:#111827;font-size:14px;vertical-align:top;\">{value}</td></tr>"
    )


def _template_base(subject: str, header_color: str, header_subtitle: str, body_html: str, date_alerte: str) -> tuple[str, str]:
    html = (
        _wrap_html(
            _render_header(header_color, "StudentTrack — ESITH Casablanca", header_subtitle)
            + "<tr><td style=\"padding:24px 24px 0 24px;color:#111827;font-size:14px;line-height:1.7;\">"
            + body_html
            + "</td></tr>"
            + _render_footer(date_alerte)
        )
    )
    return subject, html


def template_etudiant_20(data) -> tuple[str, str]:
    sujet = f"⚠️ Avertissement absences — {data.get('module_name', '')}"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour {data.get('student_name', '')},</p>"
        f"<p style=\"margin:0 0 16px 0;\">Nous vous informons que votre taux d'absences non justifiées dans le module <strong>{data.get('module_name', '')}</strong> a atteint <strong>{data.get('taux_absence', '')}</strong>, dépassant le seuil de <strong>{data.get('seuil', '')}</strong>.</p>"
        f"<p style=\"margin:0 0 16px 0;\">Si cette situation persiste, vous risquez de perdre votre droit de passer l'examen de ce module.</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#fff7ed;border:1px solid #fcd9b6;border-radius:8px;margin:16px 0;padding:16px;\">"
        f"<tr><td style=\"color:#92400e;font-size:14px;\"><strong>Situation actuelle</strong></td></tr>"
        f"<tr><td style=\"padding-top:10px;color:#374151;font-size:14px;\">Module : {data.get('module_name', '')}</td></tr>"
        f"<tr><td style=\"color:#374151;font-size:14px;\">Taux d'absence : {data.get('taux_absence', '')}</td></tr>"
        f"<tr><td style=\"color:#374151;font-size:14px;\">Score global : {data.get('score_global', '')}/100</td></tr>"
        f"</table>"
        f"<p style=\"margin:0 0 16px 0;\">Nous vous invitons à contacter la scolarité immédiatement.</p>"
        f"<p style=\"margin:0;\"><a href=\"mailto:scolarite@esith.ma\" style=\"color:#F97316;font-weight:700;text-decoration:none;\">Contacter la scolarité</a></p>"
    )
    return _template_base(sujet, "#F97316", "Avertissement absences", body, date_alerte)


def template_etudiant_30(data) -> tuple[str, str]:
    sujet = f"🚨 Alerte absences — {data.get('module_name', '')} — Action requise"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour {data.get('student_name', '')},</p>"
        f"<p style=\"margin:0 0 16px 0;\">Votre taux d'absences non justifiées dans le module <strong>{data.get('module_name', '')}</strong> est de <strong>{data.get('taux_absence', '')}</strong>.<br>"
        f"Cela constitue un second seuil d'alerte après le précédent avertissement.</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"background:#fee2e2;border:1px solid #fecaca;border-radius:8px;margin:16px 0;padding:16px;\">"
        f"<tr><td style=\"color:#991b1b;font-size:14px;\"><strong>Rapport transmis au chef de filière</strong></td></tr>"
        f"<tr><td style=\"padding-top:10px;color:#374151;font-size:14px;\">Taux actuel : {data.get('taux_absence', '')}</td></tr>"
        f"<tr><td style=\"color:#374151;font-size:14px;\">Seuil : {data.get('seuil', '')}</td></tr>"
        f"</table>"
        f"<p style=\"margin:0 0 16px 0;\">Contactez la scolarité sans délai pour régulariser votre situation.</p>"
        f"<p style=\"margin:0;\"><a href=\"mailto:scolarite@esith.ma\" style=\"color:#EF4444;font-weight:700;text-decoration:none;\">Contacter la scolarité</a></p>"
    )
    return _template_base(sujet, "#EF4444", "Alerte absences — Action requise", body, date_alerte)


def template_etudiant_50(data) -> tuple[str, str]:
    sujet = f"🔴 EXCLUSION EXAMEN — {data.get('module_name', '')} — {data.get('student_name', '')}"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour {data.get('student_name', '')},</p>"
        f"<p style=\"margin:0 0 16px 0;\">Votre taux d'absences total dans le module <strong>{data.get('module_name', '')}</strong> a atteint <strong>{data.get('taux_absence', '')}</strong>.<br>"
        f"Conformément au règlement, votre accès à l'examen de ce module est bloqué.</p>"
        f"<p style=\"margin:0 0 16px 0;font-weight:700;color:#7f1d1d;\">Démarche de régularisation :</p>"
        f"<ol style=\"margin:0 0 16px 0;padding-left:18px;color:#111827;font-size:14px;line-height:1.7;\">"
        f"<li>Contactez la scolarité immédiatement.</li>"
        f"<li>Fournissez les pièces justificatives nécessaires.</li>"
        f"<li>Demandez une dérogation officielle avant la date d'examen.</li>"
        f"</ol>"
        f"<p style=\"margin:0;\"><a href=\"mailto:scolarite@esith.ma\" style=\"color:#7f1d1d;font-weight:700;text-decoration:none;\">Contacter la scolarité</a></p>"
    )
    return _template_base(sujet, "#7F1D1D", "EXCLUSION EXAMEN — Décision officielle", body, date_alerte)


def template_chef_filiere_30(data) -> tuple[str, str]:
    sujet = f"📊 Alerte absences — {data.get('student_name', '')} — {data.get('module_name', '')}"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour,</p>"
        f"<p style=\"margin:0 0 16px 0;\">Un(e) étudiant(e) de votre filière présente un seuil d'absences dépassé.</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse;margin-bottom:16px;\">"
        f"{_bold_row('Étudiant', data.get('student_name', ''))}"
        f"{_bold_row('ID', data.get('student_id', ''))}"
        f"{_bold_row('Filière', data.get('filiere', ''))}"
        f"{_bold_row('Module', data.get('module_name', ''))}"
        f"{_bold_row('Taux', data.get('taux_absence', ''))}"
        f"{_bold_row('Score global', str(data.get('score_global', '')) + '/100')}"
        f"</table>"
        f"<p style=\"margin:0 0 16px 0;\">Accédez au dashboard pour suivre l'étudiant et proposer un plan d'action.</p>"
        f"<p style=\"margin:0;\"><a href=\"http://localhost:5173\" style=\"color:#F97316;font-weight:700;text-decoration:none;\">Ouvrir le dashboard</a></p>"
    )
    return _template_base(sujet, "#F97316", "Alerte absences — Chef de filière", body, date_alerte)


def template_chef_filiere_50(data) -> tuple[str, str]:
    sujet = f"🚨 Exclusion imminente — {data.get('student_name', '')} — {data.get('module_name', '')}"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour,</p>"
        f"<p style=\"margin:0 0 16px 0;\">Le cas de <strong>{data.get('student_name', '')}</strong> est critique : le taux d'absences dans <strong>{data.get('module_name', '')}</strong> est de <strong>{data.get('taux_absence', '')}</strong>.</p>"
        f"<p style=\"margin:0 0 16px 0;\">L'accès examen est actuellement bloqué automatiquement.</p>"
        f"<p style=\"margin:0 0 16px 0;font-weight:700;color:#b91c1c;\">Actions recommandées :</p>"
        f"<ul style=\"margin:0 0 16px 0;padding-left:18px;color:#111827;font-size:14px;line-height:1.7;\">"
        f"<li>Entretien pédagogique avec l'étudiant.</li>"
        f"<li>Contact avec les parents si nécessaire.</li>"
        f"<li>Coordination avec la discipline et la scolarité.</li>"
        f"</ul>"
        f"<p style=\"margin:0;\"><a href=\"http://localhost:5173\" style=\"color:#EF4444;font-weight:700;text-decoration:none;\">Voir le dashboard</a></p>"
    )
    return _template_base(sujet, "#EF4444", "Exclusion imminente — Chef de filière", body, date_alerte)


def template_direction_50(data) -> tuple[str, str]:
    sujet = f"🔴 Rapport Exclusion — {data.get('filiere', '')} — {data.get('student_name', '')}"
    date_alerte = data.get('date_alerte', '')
    body = (
        f"<p style=\"margin:0 0 16px 0;\">Bonjour,</p>"
        f"<p style=\"margin:0 0 16px 0;\">Rapport exécutif sur un étudiant en situation d'exclusion aux examens.</p>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin-bottom:16px;border-collapse:collapse;\">"
        f"<tr>"
        f"<td width=\"33%\" style=\"background:#111827;color:#ffffff;padding:14px;border-radius:8px 0 0 8px;text-align:center;font-size:14px;\"><strong>Étudiant</strong><br>{data.get('student_name', '')}</td>"
        f"<td width=\"33%\" style=\"background:#1f2937;color:#ffffff;padding:14px;text-align:center;font-size:14px;\"><strong>Taux</strong><br>{data.get('taux_absence', '')}</td>"
        f"<td width=\"34%\" style=\"background:#111827;color:#ffffff;padding:14px;border-radius:0 8px 8px 0;text-align:center;font-size:14px;\"><strong>Score</strong><br>{data.get('score_global', '')}/100</td>"
        f"</tr></table>"
        f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border:1px solid #e5e7eb;border-radius:8px;border-collapse:collapse;\">"
        f"<tr style=\"background:#f3f4f6;color:#374151;font-size:14px;\">"
        f"<th align=\"left\" style=\"padding:12px;\">Filière</th>"
        f"<th align=\"left\" style=\"padding:12px;\">Module</th>"
        f"<th align=\"left\" style=\"padding:12px;\">ID étudiant</th>"
        f"<th align=\"left\" style=\"padding:12px;\">Statut</th>"
        f"</tr>"
        f"<tr style=\"color:#111827;font-size:14px;\">"
        f"<td style=\"padding:12px;border-top:1px solid #e5e7eb;\">{data.get('filiere', '')}</td>"
        f"<td style=\"padding:12px;border-top:1px solid #e5e7eb;\">{data.get('module_name', '')}</td>"
        f"<td style=\"padding:12px;border-top:1px solid #e5e7eb;\">{data.get('student_id', '')}</td>"
        f"<td style=\"padding:12px;border-top:1px solid #e5e7eb;\"><strong>BLOQUÉ</strong></td>"
        f"</tr></table>"
        f"<p style=\"margin:16px 0 16px 0;color:#374151;font-size:14px;line-height:1.7;\">Année scolaire : {data.get('annee_scolaire', '2024-2025')}</p>"
        f"<p style=\"margin:0;\"><a href=\"http://localhost:5173\" style=\"color:#111827;font-weight:700;text-decoration:none;\">Ouvrir le dashboard</a></p>"
        f"<p style=\"margin:16px 0 0 0;color:#6b7280;font-size:12px;\"><strong>Document confidentiel</strong></p>"
    )
    return _template_base(sujet, "#111827", "Rapport Exclusion — Direction", body, date_alerte)
