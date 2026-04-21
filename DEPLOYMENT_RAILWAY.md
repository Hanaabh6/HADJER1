# Déploiement Backend sur Railway

Guide complet pour déployer le backend FastAPI sur Railway.app (gratuit et rapide).

## Prérequis

- [Railway.app](https://railway.app) - Créer un compte gratuit
- [GitHub](https://github.com) - Connecter ton repo (déjà fait)
- MongoDB (Supabase) - Base de données (déjà configurée)

---

## 1️⃣ Créer un compte Railway

1. Aller sur https://railway.app
2. Cliquer "Start Free" 
3. Connecter avec GitHub
4. Autoriser Railway à accéder à tes repos

---

## 2️⃣ Créer un nouveau projet Railway

### Option A: Déployer depuis GitHub (recommandé)

1. Dans Railway Dashboard, cliquer **"New Project"**
2. Cliquer **"Deploy from GitHub"**
3. Sélectionner le repo `Hanaabh6/HADJER1`
4. Sélectionner la branche (ou garder `main`)
5. Cliquer **"Deploy"**

Railway va :
- Lire le `Dockerfile`
- Construire l'image
- Lancer le service

### Option B: Déployer depuis CLI (avancé)

```bash
# Installer Railway CLI
npm i -g @railway/cli

# Se connecter
railway login

# Se placer dans le repo
cd c:\Users\ASUS\Downloads\20.4

# Créer un projet Railway
railway init
# Suivre les prompts

# Lancer le déploiement
railway up
```

---

## 3️⃣ Configurer les variables d'environnement

**Dans Railway Dashboard :**

1. Ouvrir le projet
2. Aller dans l'onglet **"Variables"** (ou **"Environment"**)
3. Ajouter les variables (copier depuis `.env`) :

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_PHONE_KEY=your-phone-key
DATABASE_URL=postgresql://user:password@localhost:5432/intellibuild
ENVIRONMENT=production
FRONTEND_ORIGINS=https://ton-frontend.com,http://localhost:5500
CORS_ORIGINS=["https://ton-frontend.com","http://localhost:5500"]
```

⚠️ **Important:** Ne pas committer `.env` avec les vraies clés - utiliser `.env.example` comme modèle.

---

## 4️⃣ Obtenir l'URL publique

Une fois déployé :

1. Aller dans **Railway Dashboard > Project > Services**
2. Cliquer sur le service FastAPI
3. Onglet **"Deployments"**
4. Copier l'URL (ex: `https://pfe-app-prod.railway.app`)

**Cette URL est ton `BACKEND_URL`** à utiliser dans :
- Frontend (config.js)
- Termux (TERMUX_DEVICE_CLIENT.js)

---

## 5️⃣ Vérifier le déploiement

```bash
# Tester l'API
curl https://ton-app.railway.app/

# Devrait retourner:
# {"message":"API is running"}

# Vérifier la doc API
# https://ton-app.railway.app/docs

# Vérifier les logs
# https://ton-app.railway.app/logs
```

---

## 6️⃣ Déploiements futurs

### Auto-déploiement (GitHub)
À chaque `git push` sur `main`, Railway redéploie automatiquement. ✅

### Déploiement manuel
```bash
# Pullez les changements
git pull origin main

# Push vers Railway
railway deploy
```

---

## 7️⃣ Mettre à jour le Frontend & Termux

Maintenant que le backend est sur Railway:

### Frontend (config.js)
```javascript
window.APP_CONFIG.API_BASE = "https://ton-app.railway.app";
```

### Termux (TERMUX_DEVICE_CLIENT.js)
```bash
export BACKEND_URL="https://ton-app.railway.app"
node TERMUX_DEVICE_CLIENT.js
```

---

## 8️⃣ Monitoring et Logs

### Voir les logs en temps réel
```bash
railway logs
```

### Dashboard Railway
- **Deployments**: Historique des déploiements
- **Metrics**: CPU, RAM, requêtes/sec
- **Logs**: Logs de l'application
- **Settings**: Configuration du projet

---

## 9️⃣ Troubleshooting

### Erreur "Build failed"
```
Vérifier les logs:
1. Railway Dashboard > Deployments > Logs
2. Chercher les erreurs de build
3. Vérifier que requirements.txt existe et les dépendances sont à jour
```

### Erreur "Connection refused" depuis Termux
```
1. Vérifier que l'URL Railway est correcte
2. Vérifier que le backend est "Running" (pas "Crashed")
3. Voir les logs du backend
4. Tester avec curl: curl https://ton-app.railway.app/
```

### Erreur CORS
```python
# Si les requêtes du frontend/Termux sont bloquées:

# Mettre à jour dans backend/main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ton-frontend.railway.app",
        "https://ton-app.railway.app",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔟 Limites gratuites Railway

| Ressource | Limite |
|-----------|--------|
| Compute | $5/mois (inclus) |
| RAM | 512 MB |
| Disk | 10 GB |
| Bandwidth | Illimité |
| Databases | 1 PostgreSQL (gratuit) |

✅ **Suffisant pour un prototype/démo**

Si tu dépasses, tu paieras à l'utilisation (modéré).

---

## ⬆️ Déployer depuis une branche (optionnel)

Pour déployer la branche `feature/termux-integration` :

1. Railway Dashboard > Services > Connexions
2. Configurer le branch
3. Sélectionner `feature/termux-integration`
4. Redéployer

Ou créer un **staging** séparé pour tester avant de merge vers `main`.

---

## Résumé rapide

```bash
# 1. Push vers GitHub
git push

# 2. Railway auto-redéploie
# (Vérifier dans Railway Dashboard)

# 3. Récupérer l'URL
# https://ton-app.railway.app

# 4. Mettre à jour config.js et Termux
# API_BASE = "https://ton-app.railway.app"

# 5. Test
# curl https://ton-app.railway.app/
```

---

**Version:** 1.0  
**Date:** 2026-04-21  
**Plateforme:** Railway.app  
**Cost:** Gratuit jusqu'à $5/mois
