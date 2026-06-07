Bug dans le système d'authentification étudiant :
Quand un étudiant n'a pas encore de mot de passe (première connexion), 
le système devrait afficher le formulaire de création de mot de passe.
Mais actuellement il affiche "mot de passe incorrect".

Vérifie dans Login.jsx :
- L'appel à /api/auth/check-email retourne bien has_password: false pour nadia.zouiten@esith.net ?
- Si has_password = false → afficher le formulaire d'inscription (création mot de passe)
- Si has_password = true → afficher le formulaire de connexion

Vérifie aussi dans app.py que l'endpoint /api/auth/check-email :
- Lit bien le fichier passwords.json
- Retourne has_password: false si l'email n'est pas dans passwords.json
- Retourne has_password: true si l'email EST dans passwords.json

Teste avec nadia.zouiten@esith.net — doit afficher "Première connexion — créez votre mot de passe"