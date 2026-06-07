Fais ces deux choses dans l'ordre :

ÉTAPE 1 — Ajouter Najlaa Larche dans le dataset

Dans data/dataset.xlsx :

Feuille Etudiants, ajoute une ligne :
- id_etudiant: 20200
- Nom: Larche
- Prenom: Najlaa
- Email_Etudiant: najlaa.larche@esith.net
- Filiere: Génie Industriel
- Code_Filiere: GI
- Annee: GI1
- Genre: F

Feuille Absences, ajoute 8 lignes pour id_etudiant 20200 :
- Module : "Gestion de Production"
- Total_Seances_Module : 26
- Excuse : Non
- DureeDecimal : 1.5
- Dates variées entre janvier et mai 2026
- Cursus : GI1
- Filiere : Génie Industriel

8 absences NJ sur 26 séances = 30.7% → dépasse seuil 20% → doit déclencher AVERTISSEMENT

ÉTAPE 2 — Configurer l'envoi email avec Brevo

Crée un fichier .env à la racine du projet :
BREVO_API_KEY=<voir_.env>
EMAIL_SENDER=studenttrack.esith@gmail.com
EMAIL_SENDER_NAME=StudentTrack ESITH Casablanca
EMAIL_ADMIN=administration@esith.net

Installe : pip install requests python-dotenv

Dans backend/agent/ia_agent.py, ajoute send_email(to_email, subject, body_html) :
- POST https://api.brevo.com/v3/smtp/email
- Headers : {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}
- Body : {
    "sender": {"name": EMAIL_SENDER_NAME, "email": EMAIL_SENDER},
    "to": [{"email": to_email}],
    "subject": subject,
    "htmlContent": body_html
  }

Appelle send_email() dans traiter_alertes() :
- taux_nj >= 20% ET avert_email_envoye = False → email AVERTISSEMENT à l'étudiant
- taux_total >= 50% ET exclu_email_envoye = False → email EXCLUSION à l'étudiant
- Sauvegarder l'état dans data/emails_log.json pour éviter les doublons

Format HTML email AVERTISSEMENT :
<h2 style="color:#1a3a6b">Avertissement — Absences ESITH</h2>
<p>Madame/Monsieur <strong>{nom}</strong>,</p>
<p>Votre taux d'absences non justifiées dans le module <strong>{module}</strong> a atteint <strong>{taux_nj}%</strong>.</p>
<p>Le seuil critique est fixé à <strong>50%</strong>. Merci de régulariser votre situation.</p>
<br>
<p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>

Format HTML email EXCLUSION :
<h2 style="color:#ef4444">Exclusion d'examen — ESITH Casablanca</h2>
<p>Madame/Monsieur <strong>{nom}</strong>,</p>
<p>Votre taux d'absences total dans le module <strong>{module}</strong> a atteint <strong>{taux_total}%</strong>.</p>
<p>Conformément au règlement, vous ne pouvez pas passer l'examen de ce module.</p>
<br>
<p style="color:#64748b">Service de la Scolarité — ESITH Casablanca — StudentTrack</p>

Ajoute .env et data/emails_log.json dans .gitignore.

ÉTAPE 3 — Tester
Relance python backend/api/app.py puis appelle 
python backend/agent/ia_agent.py
Doit envoyer un vrai email à najlaa.larche@esith.net depuis studenttrack.esith@gmail.com