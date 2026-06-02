# 🚀 Setup EmailJS pour StudentTrack

## ✅ Étapes complétées

- [x] Installation de `@emailjs/browser`
- [x] Création du service `emailService.js`
- [x] Création des 6 templates EmailJS documentés
- [x] Configuration de `.env.local`
- [x] Intégration dans `PageAlertes.jsx`
- [x] Anti-doublon localStorage implémenté

---

## 📋 Configuration requise

### 1. Créer un compte EmailJS

1. Allez sur https://www.emailjs.com/
2. Inscrivez-vous gratuitement
3. Confirmez votre email

### 2. Configurer un Service Email

**Option A : Gmail**
1. Dans EmailJS Dashboard → Email Services → Create Service
2. Sélectionnez "Gmail"
3. Cliquez sur "Connect Account"
4. Authentifiez-vous avec votre Gmail
5. Complétez la configuration
6. **Notez votre `SERVICE_ID`** (ex: `service_abc123xyz`)

**Option B : Autre provider (Outlook, SendGrid, etc.)**
- Suivez les instructions du provider correspondant sur EmailJS

### 3. Obtenir votre Public Key

1. Allez dans **Account** → **API Keys**
2. Copiez votre **Public Key** (commence par `pk_` ou similaire)

### 4. Créer les 6 Templates

1. Allez dans **Email Templates**
2. Cliquez **Create Template**
3. Pour chaque template ci-dessous :
   - Remplissez le **Template Name** exactement comme spécifié
   - Collez le **HTML** fourni dans [emailTemplates.md](./emailTemplates.md)
   - Cliquez **Save**

#### 📧 Templates à créer

| Nom Template | ID à utiliser | Sujet |
|---|---|---|
| `etudiant_20` | `template_etudiant_20` | ⚠️ Avertissement absences |
| `etudiant_30` | `template_etudiant_30` | 🚨 Alerte absences — Action requise |
| `etudiant_50` | `template_etudiant_50` | 🔴 EXCLUSION EXAMEN |
| `chef_30` | `template_chef_30` | 📊 Alerte absences |
| `chef_50` | `template_chef_50` | 🚨 Exclusion imminente |
| `direction_50` | `template_direction_50` | 🔴 Rapport exclusion |

**⚠️ Important :** Les noms doivent correspondre **exactement** à ceux dans `.env.local`

### 5. Configurer `.env.local`

Modifiez le fichier `dashboard/.env.local` :

```env
VITE_EMAILJS_PUBLIC_KEY=pk_xxxxxxxxxxxxx
VITE_EMAILJS_SERVICE_ID=service_xxxxxxxxxxxxx
VITE_TPL_ETUDIANT_20=template_etudiant_20
VITE_TPL_ETUDIANT_30=template_etudiant_30
VITE_TPL_ETUDIANT_50=template_etudiant_50
VITE_TPL_CHEF_30=template_chef_30
VITE_TPL_CHEF_50=template_chef_50
VITE_TPL_DIRECTION_50=template_direction_50
```

---

## 🧪 Tester avec votre mail

L'utilisateur a fourni : **kroumirihab@gmail.com**

1. **Configurez Gmail comme service EmailJS** (voir étape 2 Option A)
2. **Créez les templates** avec cette adresse
3. **Testez le bouton "📧 Envoyer les alertes"** dans la page Alertes admin

---

## 🔄 Flux d'envoi des alertes

### 1. Admin clique "📧 Envoyer les alertes"

```
PageAlertes.jsx → handleSendAlerts()
   ↓
Pour chaque étudiant dans alertes[]
   ↓
processAlerts(etudiant, contacts)
   ↓
For each module_en_alerte:
   ├─ if taux_nj >= 20% → sendAlert(seuil: 20, dest: etudiant)
   ├─ if taux_nj >= 30% → sendAlert(seuil: 30, dest: etudiant)
   │                    → sendAlert(seuil: 30, dest: chef)
   └─ if taux_total >= 50% → sendAlert(seuil: 50, dest: etudiant)
                            → sendAlert(seuil: 50, dest: chef)
                            → sendAlert(seuil: 50, dest: direction)
```

### 2. Anti-doublon localStorage

- Chaque email envoyé = clé localStorage : `st_alert_{studentId}_{module}_{seuil}`
- Empêche les doublons même si on clique 2 fois
- Les clés persistent en session

### 3. Résultat

✅ Emails envoyés via EmailJS  
✅ Destinataires notifiés  
✅ Logs localStorage pour audit

---

## 🛠️ Troubleshooting

### ❌ "TEMPLATES not found"
→ Vérifiez les noms de templates dans `.env.local`  
→ Assurez-vous que les templates existent dans EmailJS Dashboard

### ❌ "PUBLIC_KEY undefined"
→ `.env.local` n'est pas chargé  
→ Relancez `npm run dev`  
→ Vérifiez que `VITE_` est présent (pas `REACT_`)

### ❌ "Service ID invalid"
→ Vérifiez la clé `VITE_EMAILJS_SERVICE_ID` dans `.env.local`

### ❌ "Emails non reçus"
→ Vérifiez les templates HTML (pas d'erreur de syntaxe)  
→ Testez l'email directement dans EmailJS Dashboard

### ❌ "CORS error"
→ EmailJS fonctionne en frontend uniquement  
→ Le CORS est géré par EmailJS (pas de problème attendu)

---

## 📝 Variables disponibles dans les templates

Tous les templates reçoivent :

| Variable | Format | Exemple |
|----------|--------|---------|
| `{{to_name}}` | Prénom Nom | Jean Dupont |
| `{{student_name}}` | Prénom Nom | Jean Dupont |
| `{{student_id}}` | ID | 12345 |
| `{{filiere}}` | Filière | IWEB5 |
| `{{module_name}}` | Module | Algorithmique |
| `{{taux_absence}}` | %age | 25% |
| `{{seuil}}` | %age | 20% |
| `{{score_global}}` | /100 | 67 |
| `{{date_alerte}}` | JJ/MM/YYYY | 02/06/2026 |

---

## 🔐 Sécurité

✅ **Public Key** → Sans danger, pour frontend  
✅ **Service ID** → Spécifique à EmailJS, visible en frontend (normal)  
✅ **.env.local** → Ignoré par Git (`*.local` dans `.gitignore`)  
✅ **Anti-doublon localStorage** → Pas de stockage backend

---

## 📦 Dépendances

```json
{
  "dependencies": {
    "@emailjs/browser": "^4.0.0"
  }
}
```

Installé via :
```bash
cd dashboard
npm install @emailjs/browser
```

---

## 🎯 Prochaines étapes

1. **Setup EmailJS** (étapes 1-5 ci-dessus)
2. **Configurer `.env.local`** avec les clés
3. **Tester** le bouton sur la page Alertes admin
4. **Vérifier les emails reçus** (kroumirihab@gmail.com)
5. **Adapter les addresses email** du chef de filière et direction selon votre organisation

---

## 📧 Support

- EmailJS Docs : https://www.emailjs.com/docs/
- GitHub Issues : https://github.com/najlaalarche/studenttrack/issues
