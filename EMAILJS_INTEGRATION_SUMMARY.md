# 📋 Résumé de l'intégration EmailJS — StudentTrack

## ✅ Fichiers créés

### 1. **`dashboard/src/services/emailService.js`**
   - Fonction `sendAlert()` : envoie un email via EmailJS
   - Fonction `processAlerts()` : traite les 3 seuils d'alerte (20%, 30%, 50%)
   - Anti-doublon localStorage : empêche les emails en doublon
   - Variables d'environnement VITE_ pour les clés EmailJS et template IDs

### 2. **`dashboard/src/services/emailTemplates.md`**
   - 6 templates HTML prêts à copier-coller dans EmailJS Dashboard
   - **etudiant_20** (orange) : avertissement bienveillant
   - **etudiant_30** (rouge) : alerte sérieuse
   - **etudiant_50** (rouge foncé) : exclusion examen confirmée
   - **chef_30** (orange) : notification au chef de filière
   - **chef_50** (rouge) : situation critique
   - **direction_50** (rouge foncé) : rapport exécutif direction
   - Styles inline (compatible Gmail, Outlook)

### 3. **`dashboard/.env.local`**
   - Template vierge des variables d'environnement à remplir
   - Ignoré par Git (*.local dans .gitignore)

### 4. **`dashboard/EMAILJS_SETUP.md`**
   - Guide complet d'installation et configuration
   - Étapes Gmail / EmailJS
   - Troubleshooting
   - Architecture du flux d'envoi

---

## 🔄 Fichiers modifiés

### **`dashboard/src/pages/admin/PageAlertes.jsx`**
   - ✅ Import de `processAlerts` depuis emailService
   - ✅ Ajout du state `emailSending` pour UI loader
   - ✅ Fonction `handleSendAlerts()` qui envoie emails pour tous les étudiants
   - ✅ Bouton "📧 Envoyer les alertes" dans l'en-tête (rouge, avec loader)

---

## 📦 Dépendances installées

```bash
npm install @emailjs/browser
```
✅ Complétée dans `dashboard/node_modules/`

---

## 🚀 Prochaines étapes (à faire par l'utilisateur)

### 1. **Configuration EmailJS**
   ```bash
   1. Aller sur emailjs.com → Créer un compte
   2. Ajouter un Service Email (Gmail recommandé)
   3. Créer 6 Email Templates avec les noms :
      - template_etudiant_20
      - template_etudiant_30
      - template_etudiant_50
      - template_chef_30
      - template_chef_50
      - template_direction_50
   4. Copier les HTML depuis dashboard/src/services/emailTemplates.md
   ```

### 2. **Remplir `.dashboard/.env.local`**
   ```env
   VITE_EMAILJS_PUBLIC_KEY=pk_xxxxxxxx  (de EmailJS Account)
   VITE_EMAILJS_SERVICE_ID=service_xxx  (de EmailJS Email Service)
   VITE_TPL_ETUDIANT_20=template_etudiant_20
   VITE_TPL_ETUDIANT_30=template_etudiant_30
   VITE_TPL_ETUDIANT_50=template_etudiant_50
   VITE_TPL_CHEF_30=template_chef_30
   VITE_TPL_CHEF_50=template_chef_50
   VITE_TPL_DIRECTION_50=template_direction_50
   ```

### 3. **Tester**
   ```bash
   cd dashboard
   npm run dev
   # Accéder à la page Alertes admin
   # Cliquer le bouton "📧 Envoyer les alertes"
   # Vérifier les emails reçus
   ```

### 4. **Adapter les emails**
   - Chef de filière : `etudiant.chef_filiere_email` (à adapter si structure différente)
   - Direction : `direction@esith.ma` (à remplacer par adresse réelle)

---

## 🔑 Architecture du flux

```
PageAlertes.jsx
    ↓
[Utilisateur clique "📧 Envoyer les alertes"]
    ↓
handleSendAlerts()
    ↓
for each étudiant:
    ├─ processAlerts(étudiant, contacts)
    │   ├─ for each module_en_alerte:
    │   │   ├─ if taux_nj >= 20% → sendAlert(seuil: 20, dest: étudiant)
    │   │   ├─ if taux_nj >= 30% → sendAlert(seuil: 30, dest: étudiant, chef)
    │   │   └─ if taux_total >= 50% → sendAlert(seuil: 50, dest: étudiant, chef, direction)
    │   └─ localStorage anti-doublon
    └─ EmailJS.send(SERVICE_ID, TEMPLATE_ID, params)

✅ Emails envoyés
📧 Destinataires notifiés
```

---

## 📊 Variables disponibles dans les templates

Chaque email reçoit ces variables de substitution :

```
{{to_name}}        → Prénom Nom (destinataire)
{{student_name}}   → Prénom Nom (étudiant)
{{student_id}}     → ID étudiant
{{filiere}}        → Filière
{{module_name}}    → Nom module
{{taux_absence}}   → Pourcentage (ex: 25%)
{{seuil}}          → Seuil franchi (ex: 20%)
{{score_global}}   → /100
{{date_alerte}}    → DD/MM/YYYY
```

---

## 🛡️ Sécurité & Bonnes pratiques

✅ **Frontend uniquement** — Pas de backend, pas de Claude API  
✅ **Public Key sûre** — Visible en frontend (conçu pour)  
✅ **Anti-doublon localStorage** — Audit trail local  
✅ **.env.local gitignorée** — Pas de commit des clés  
✅ **Styles inline** — Compatible tous les email clients  

---

## 🧪 Test avec kroumirihab@gmail.com

L'utilisateur a fourni **kroumirihab@gmail.com** pour tester :

1. Configurez Gmail comme service EmailJS
2. Dans les templates, utilisez cette adresse
3. Déclenchez l'envoi
4. Vérifiez la réception

---

## 📞 Fichiers à consulter

- **Setup complet** → `dashboard/EMAILJS_SETUP.md`
- **Service EmailJS** → `dashboard/src/services/emailService.js`
- **Templates HTML** → `dashboard/src/services/emailTemplates.md`
- **Page Alertes intégrée** → `dashboard/src/pages/admin/PageAlertes.jsx`
- **Variables env** → `dashboard/.env.local`

---

## ✨ Prêt à être déployé !

Tous les fichiers sont en place. Il suffit de :
1. Configurer EmailJS
2. Remplir .env.local
3. Tester

L'intégration respecte 100% les spécifications fournies :
- ✅ EmailJS uniquement (pas Claude API)
- ✅ Frontend React uniquement
- ✅ Anti-doublon localStorage
- ✅ 6 templates différenciés
- ✅ 3 seuils (20%, 30%, 50%)
- ✅ 3 destinataires (étudiant, chef, direction)
