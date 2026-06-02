# 📧 Templates EmailJS — StudentTrack

**Variables disponibles dans tous les templates :**
- `{{to_name}}` — Prénom Nom du destinataire
- `{{student_name}}` — Prénom Nom de l'étudiant
- `{{student_id}}` — ID unique étudiant
- `{{filiere}}` — Filière de l'étudiant
- `{{module_name}}` — Nom du module
- `{{taux_absence}}` — Taux actuel (ex: "25%")
- `{{seuil}}` — Seuil franchi (ex: "20%")
- `{{score_global}}` — Score global /100
- `{{date_alerte}}` — Date d'alerte en format FR (ex: "02/06/2026")

---

## TEMPLATE 1 : `etudiant_20`

**Sujet :**
```
⚠️ Avertissement absences — {{module_name}}
```

**Destinataire :** Étudiant  
**Couleur header :** #F97316 (orange)  
**Ton :** Préventif, bienveillant

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #F97316; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">⚠️ Avertissement Absences</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 16px 0; font-size: 14px;">Bonjour <strong>{{to_name}}</strong>,</p>

              <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6;">
                Nous vous contactons pour vous informer qu'un <strong>seuil d'absences</strong> a été franchi 
                dans le module <strong>{{module_name}}</strong> de votre filière <strong>{{filiere}}</strong>.
              </p>

              <div style="background: #FFF5F0; border-left: 4px solid #F97316; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #666;">
                  <strong>Situation actuelle :</strong>
                </p>
                <p style="margin: 0 0 4px 0; font-size: 13px;">
                  • Taux d'absence : <strong>{{taux_absence}}</strong>
                </p>
                <p style="margin: 0 0 4px 0; font-size: 13px;">
                  • Seuil critère : <strong>{{seuil}}</strong>
                </p>
                <p style="margin: 0; font-size: 13px;">
                  • Score global : <strong>{{score_global}}/100</strong>
                </p>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.6;">
                <strong>⏰ Conséquences si aucune action :</strong><br>
                Si le taux d'absences continue d'augmenter, vous risquez une exclusion des examens.
              </p>

              <p style="margin: 0 0 12px 0; font-size: 14px; line-height: 1.6;">
                <strong>✅ Recommandation :</strong><br>
                Nous vous encourageons vivement à régulariser votre situation au plus tôt. 
                Contactez la scolarité si vous avez une raison justifiée.
              </p>

              <p style="margin: 20px 0 0 0; font-size: 13px; color: #666; line-height: 1.6;">
                Si vous avez des questions, veuillez contacter la scolarité.<br>
                <strong>Date d'alerte :</strong> {{date_alerte}}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## TEMPLATE 2 : `etudiant_30`

**Sujet :**
```
🚨 Alerte absences — {{module_name}} — Action requise
```

**Destinataire :** Étudiant  
**Couleur header :** #EF4444 (rouge)  
**Ton :** Sérieux, clair

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #EF4444; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">🚨 Alerte Absences — Action Requise</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 16px 0; font-size: 14px;"><strong>{{to_name}}</strong>,</p>

              <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6;">
                <strong>SITUATION CRITIQUE :</strong> Votre taux d'absences dans le module 
                <strong>{{module_name}}</strong> a atteint <strong>{{taux_absence}}</strong>, 
                dépassant le seuil d'alerte <strong>{{seuil}}</strong>.
              </p>

              <div style="background: #FEE2E2; border-left: 4px solid #EF4444; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #666; font-weight: 600;">
                  ⚠️ Rappel de l'avertissement précédent
                </p>
                <p style="margin: 0 0 8px 0; font-size: 13px;">
                  Vous avez été informé lors du dépassement du seuil 20%.
                </p>
                <p style="margin: 0; font-size: 13px;">
                  Cette deuxième alerte vous demande une <strong>action immédiate</strong>.
                </p>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: #EF4444;">
                📞 Action requise : Contactez la scolarité SANS DÉLAI
              </p>

              <p style="margin: 0 0 16px 0; font-size: 13px; line-height: 1.6; color: #666;">
                • Score global : {{score_global}}/100<br>
                • Filière : {{filiere}}<br>
                • Date d'alerte : {{date_alerte}}
              </p>

              <p style="margin: 0; font-size: 13px; color: #666; line-height: 1.6;">
                Justifiez votre absence ou préparez un plan de rattrapage. Le non-respect 
                risque une exclusion aux examens.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## TEMPLATE 3 : `etudiant_50`

**Sujet :**
```
🔴 EXCLUSION EXAMEN — {{module_name}}
```

**Destinataire :** Étudiant  
**Couleur header :** #991B1B (rouge foncé)  
**Ton :** Formel, urgent

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #991B1B; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">🔴 EXCLUSION EXAMEN CONFIRMÉE</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 20px 0; font-size: 15px; font-weight: 600; color: #991B1B;">
                Avis officiel d'exclusion aux examens
              </p>

              <div style="background: #FFE4E4; border-left: 4px solid #991B1B; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0; font-size: 13px; color: #666; font-weight: 600;">
                  🔴 Blocage accès examen confirmé
                </p>
                <p style="margin: 0 0 8px 0; font-size: 13px;">
                  En raison d'un taux d'absences total de <strong>{{taux_absence}}</strong> 
                  dans le module <strong>{{module_name}}</strong>, vous êtes <strong>exclu des examens</strong>.
                </p>
                <p style="margin: 0; font-size: 13px; font-weight: 600;">
                  Cette décision est définitive jusqu'à dérogation.
                </p>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 14px; font-weight: 600;">
                ✅ Démarche de régularisation :
              </p>

              <ol style="margin: 0 0 16px 0; padding-left: 20px; font-size: 13px; line-height: 1.8;">
                <li>Contactez <strong>la scolarité immédiatement</strong></li>
                <li>Justifiez les absences avec pièces justificatives</li>
                <li>Demandez une dérogation auprès de la direction</li>
                <li>Attendez confirmation avant l'examen</li>
              </ol>

              <p style="margin: 0 0 16px 0; font-size: 13px; line-height: 1.6; color: #666;">
                <strong>Informations :</strong><br>
                • Étudiant : {{student_name}} (ID: {{student_id}})<br>
                • Filière : {{filiere}}<br>
                • Module : {{module_name}}<br>
                • Score global : {{score_global}}/100<br>
                • Date d'alerte : {{date_alerte}}
              </p>

              <p style="margin: 0; font-size: 13px; color: #991B1B; font-weight: 600;">
                ⏰ Agissez rapidement — Les délais de dérogation sont stricts.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## TEMPLATE 4 : `chef_30`

**Sujet :**
```
📊 Alerte absences — {{student_name}} — {{module_name}}
```

**Destinataire :** Chef de filière  
**Couleur header :** #F97316 (orange)  
**Ton :** Professionnel, informatif

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #F97316; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">📊 Alerte Absences</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 16px 0; font-size: 14px;">Monsieur/Madame,</p>

              <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6;">
                Un étudiant(e) de votre filière dépasse le seuil d'alerte absences.
              </p>

              <div style="background: #FFF5F0; border-left: 4px solid #F97316; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <table cellpadding="0" cellspacing="0" style="width: 100%; font-size: 13px;">
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Étudiant :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{student_name}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>ID :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{student_id}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Filière :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{filiere}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Module :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{module_name}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Taux absences :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong style="color: #F97316;">{{taux_absence}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Seuil :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{seuil}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;"><strong>Score global :</strong></td>
                    <td style="padding: 4px 0; text-align: right;"><strong>{{score_global}}/100</strong></td>
                  </tr>
                </table>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 13px; line-height: 1.6;">
                <strong>Actions recommandées :</strong><br>
                • Convoqur l'étudiant pour discussion<br>
                • Évaluer les raisons des absences<br>
                • Proposer un plan d'amélioration
              </p>

              <p style="margin: 0 0 16px 0; font-size: 12px; color: #666;">
                Date d'alerte : {{date_alerte}}<br>
                Accédez au dashboard StudentTrack pour plus de détails.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## TEMPLATE 5 : `chef_50`

**Sujet :**
```
🚨 Exclusion imminente — {{student_name}} — {{module_name}}
```

**Destinataire :** Chef de filière  
**Couleur header :** #EF4444 (rouge)  
**Ton :** Urgent, clair

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #EF4444; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">🚨 Situation Critique</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 16px 0; font-size: 14px; font-weight: 600; color: #EF4444;">
                Exclusion imminente — Action pédagogique requise
              </p>

              <div style="background: #FEE2E2; border-left: 4px solid #EF4444; padding: 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; font-size: 13px; font-weight: 600;">
                  Situation critique identifiée
                </p>
                <table cellpadding="0" cellspacing="0" style="width: 100%; font-size: 13px;">
                  <tr>
                    <td style="padding: 3px 0; color: #666;"><strong>Étudiant :</strong></td>
                    <td style="padding: 3px 0; text-align: right;"><strong>{{student_name}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 3px 0; color: #666;"><strong>Module :</strong></td>
                    <td style="padding: 3px 0; text-align: right;"><strong>{{module_name}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 3px 0; color: #666;"><strong>Taux total :</strong></td>
                    <td style="padding: 3px 0; text-align: right;"><strong style="color: #EF4444;">{{taux_absence}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 3px 0; color: #666;"><strong>Blocage examen :</strong></td>
                    <td style="padding: 3px 0; text-align: right;"><strong>CONFIRMÉ</strong></td>
                  </tr>
                </table>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 13px; line-height: 1.6; font-weight: 600;">
                Actions pédagogiques recommandées :
              </p>

              <ol style="margin: 0 0 16px 0; padding-left: 20px; font-size: 13px; line-height: 1.8; color: #666;">
                <li>Convocation immédiate avec l'étudiant</li>
                <li>Analyse des raisons des absences répétées</li>
                <li>Envisager une dérogation justifiée si nécessaire</li>
                <li>Documenter l'interaction et le plan d'action</li>
              </ol>

              <p style="margin: 0; font-size: 12px; color: #666;">
                <strong>Filière :</strong> {{filiere}}<br>
                <strong>Score global :</strong> {{score_global}}/100<br>
                <strong>Date :</strong> {{date_alerte}}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## TEMPLATE 6 : `direction_50`

**Sujet :**
```
🔴 Rapport exclusion — {{student_name}} — {{filiere}}
```

**Destinataire :** Direction  
**Couleur header :** #991B1B (rouge foncé)  
**Ton :** Formel, exécutif

**HTML :**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5;">
    <tr>
      <td align="center" style="padding: 20px;">
        <table width="600" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          
          <!-- Header -->
          <tr>
            <td style="background: #991B1B; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; font-size: 24px; font-weight: 700;">StudentTrack — ESITH Casablanca</h1>
              <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">🔴 Rapport d'Exclusion</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 30px 20px; color: #333;">
              <p style="margin: 0 0 16px 0; font-size: 14px; font-weight: 600; color: #991B1B;">
                Résumé Exécutif — Exclusion aux examens
              </p>

              <div style="background: #FFE4E4; border-left: 4px solid #991B1B; padding: 16px; margin: 20px 0; border-radius: 4px; font-size: 13px;">
                <table cellpadding="0" cellspacing="0" style="width: 100%;">
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Étudiant :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{student_name}}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>ID :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{student_id}}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Filière :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{filiere}}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Module affecté :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{module_name}}</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Taux absences total :</strong></td>
                    <td style="padding: 6px 0; text-align: right;"><strong style="color: #991B1B;">{{taux_absence}}</strong></td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Score global :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{score_global}}/100</td>
                  </tr>
                  <tr>
                    <td style="padding: 6px 0; color: #666;"><strong>Date d'exclusion :</strong></td>
                    <td style="padding: 6px 0; text-align: right;">{{date_alerte}}</td>
                  </tr>
                </table>
              </div>

              <p style="margin: 0 0 12px 0; font-size: 13px; line-height: 1.6;">
                <strong>Raison :</strong> Le seuil d'absences totales de 50% a été dépassé, 
                conformément au réglement interne de l'établissement. L'étudiant est exclu 
                de l'examen du module jusqu'à dérogation formelle.
              </p>

              <p style="margin: 0 0 12px 0; font-size: 13px; line-height: 1.6;">
                <strong>Procédure :</strong> Une communication a été envoyée à l'étudiant et 
                au chef de filière. Les demandes de dérogation doivent être formalisées 
                avant la date d'examen.
              </p>

              <p style="margin: 0; font-size: 12px; color: #666; line-height: 1.6;">
                <em>Rapport généré automatiquement par StudentTrack</em>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f9f9f9; padding: 16px 20px; text-align: center; border-top: 1px solid #e0e0e0; font-size: 11px; color: #999; border-radius: 0 0 8px 8px;">
              <p style="margin: 0;">Système automatique StudentTrack — Ne pas répondre à cet email</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
```

---

## 📋 Résumé

| Template | Sujet | Destinataire | Couleur | Seuil |
|----------|-------|--------------|--------|-------|
| etudiant_20 | ⚠️ Avertissement | Étudiant | #F97316 | 20% |
| etudiant_30 | 🚨 Alerte | Étudiant | #EF4444 | 30% |
| etudiant_50 | 🔴 Exclusion | Étudiant | #991B1B | 50% |
| chef_30 | 📊 Alerte | Chef filière | #F97316 | 30% |
| chef_50 | 🚨 Exclusion | Chef filière | #EF4444 | 50% |
| direction_50 | 🔴 Rapport | Direction | #991B1B | 50% |
