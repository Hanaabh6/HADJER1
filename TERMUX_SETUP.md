# Termux IoT Device Client

Client Node.js pour contrôler des appareils IoT (TV, lampes, etc.) via Termux sur un téléphone Android, en se connectant au backend hébergé.

## Architecture

```
Frontend Web (hébergée) 
    ↓ POST /termux/{device_id}/send-command
Backend (Railway/Render/etc)
    ↓ GET /termux/{device_id}/commands
Termux (polling) → Exécute commandes Android
```

## Installation sur Termux

### 1. Setup Termux
```bash
# Installer Node.js
pkg install nodejs

# Créer le dossier du projet
mkdir -p ~/intellibuild && cd ~/intellibuild

# Initialiser npm
npm init -y

# Installer axios (pour appels HTTP)
npm install axios
```

### 2. Copier le fichier client
```bash
# Sur ton PC, copy TERMUX_DEVICE_CLIENT.js vers le répertoire Termux
# Ou copier le contenu directement via un éditeur

# Puis dans Termux:
ls -la TERMUX_DEVICE_CLIENT.js
```

### 3. Configurer l'URL du backend
Avant de lancer, modifier les variables d'environnement ou les constantes dans le fichier:

```bash
# Option 1: Variables d'environnement (recommandé)
export BACKEND_URL="https://ton-app.railway.app"
export DEVICE_ID="termux_tv_1"
export DEVICE_NAME="Smart TV Termux"

# Option 2: Editer directement dans le fichier
nano TERMUX_DEVICE_CLIENT.js
# Chercher "// ========== CONFIG ==========" et modifier les valeurs
```

### 4. Lancer le client
```bash
node TERMUX_DEVICE_CLIENT.js
```

**Output attendu:**
```
🚀 Démarrage du client Termux IoT...
Backend URL: https://ton-app.railway.app
Device ID: termux_tv_1
📱 Enregistrement du device auprès de https://ton-app.railway.app...
✅ Device enregistré: Appareil Smart TV Termux enregistré avec succès
✅ Serveur local lancé sur 0.0.0.0:3001
✅ Polling du backend tous les 5000ms
```

---

## Utilisation

### Depuis le Frontend Web
```javascript
// Dans le frontend, utiliser le client Termux
const termuxClient = new TermuxClient("https://ton-app.railway.app");

// Envoyer une commande
await termuxClient.sendCommand(
  "termux_tv_1",        // device_id
  "play_channel",       // action
  "tv_1",              // object_id
  { channel: "tf1" }   // paramètres
);
```

### Commandes supportées

| Action | Paramètres | Exemple |
|--------|-----------|---------|
| `power_on` | - | Lance la TV |
| `power_off` | - | Éteint la TV |
| `play_channel` | `{ channel: "tf1" }` | Lance la chaîne TF1 |
| `next_channel` | - | Chaîne suivante |
| `prev_channel` | - | Chaîne précédente |
| `volume_up` | - | Volume +1 |
| `volume_down` | - | Volume -1 |
| `set_volume` | `{ level: 15 }` | Fixe volume à 15 |
| `mute` | - | Mute (volume 0) |

---

## Configuration avancée

### Personnaliser les chaînes TV
Éditer le tableau `channels` dans le fichier:
```javascript
const channels = [
  { slug: "tf1", label: "TF1", file: "tf1.mp4" },
  { slug: "france2", label: "France 2", file: "france2.mp4" },
  // Ajouter d'autres chaînes...
];
```

### Personnaliser le poll interval
```bash
export POLL_INTERVAL=3000  # 3 secondes au lieu de 5
```

### Health check local
```bash
curl http://127.0.0.1:3001/health
# Retourne:
# {
#   "ok": true,
#   "device_id": "termux_tv_1",
#   "power": "on",
#   "volume": 10,
#   "backend_connected": true
# }
```

---

## Commandes Termux disponibles

Le client utilise les commandes Android via `input keyevent` et `am start`:

| Keyevent | Action |
|----------|--------|
| 224 | Wakeup (allumer) |
| 223 | Sleep (éteindre) |
| 82 | Menu/Unlock |
| 24 | Volume up |
| 25 | Volume down |
| 4 | Back |
| 3 | Home |

---

## Logs & Debugging

### Logs en direct
```bash
# Lancer avec logs détaillés
node TERMUX_DEVICE_CLIENT.js 2>&1 | tee device.log

# Ou voir le fichier de log
tail -f device.log
```

### Vérifier la connexion backend
```bash
# Test de l'endpoint du backend
curl -X GET "https://ton-app.railway.app/termux/devices/all"
```

---

## Déploiement Termux

### Garder le client lancé en arrière-plan

**Option 1: Screen (recommandé)**
```bash
# Installer screen
pkg install screen

# Lancer dans une session screen
screen -S termux-device node TERMUX_DEVICE_CLIENT.js

# Détacher: Ctrl+A puis D
# Réattacher: screen -r termux-device
```

**Option 2: Service Termux (avancé)**
```bash
# Créer un script de démarrage
mkdir -p ~/.termux/boot
echo '#!/bin/bash
cd ~/intellibuild
node TERMUX_DEVICE_CLIENT.js' > ~/.termux/boot/device.sh
chmod +x ~/.termux/boot/device.sh

# Activer les notifications de démarrage
# Paramètres Termux > Notifications > Activer
```

---

## Troubleshooting

### Erreur "Cannot find module 'axios'"
```bash
npm install axios
```

### Erreur "Impossible de se connecter au backend"
- Vérifier l'URL: `echo $BACKEND_URL`
- Vérifier la connexion internet: `ping 8.8.8.8`
- Vérifier que le backend est accessible: `curl https://ton-app.railway.app`

### Commandes Android ne s'exécutent pas
- Vérifier les permissions Termux: Paramètres > Apps > Termux > Permissions > Appareil
- Tester manuellement: `input keyevent 24` (volume up)

### Le device n'apparaît pas dans le backend
- Vérifier les logs du client
- Vérifier que le backend reçoit bien les requêtes: `curl https://ton-app.railway.app/termux/devices/all`

---

## Architecture complète

```
┌─────────────────────────────────────┐
│     Frontend Web                    │
│  (http://localhost:5500)            │
│  - Interface utilisateur            │
│  - Envoie commandes au backend      │
└────────────┬────────────────────────┘
             │
             ▼ POST /termux/{device_id}/send-command
┌─────────────────────────────────────┐
│     Backend FastAPI                 │
│  (https://ton-app.railway.app)      │
│  - Reçoit commandes                 │
│  - Stocke dans MongoDB              │
│  - Endpoints Termux                 │
└────────────┬────────────────────────┘
             │
             ▼ GET /termux/{device_id}/commands (polling 5s)
┌─────────────────────────────────────┐
│  Ce script (Termux)                 │
│  - Polling du backend               │
│  - Exécute commandes Android        │
│  - Envoie statut au backend         │
└─────────────────────────────────────┘
```

---

## Notes importantes

1. **Permissions Android**: Le client a besoin d'accès à l'exécution de commandes (déjà inclus dans Termux)
2. **Batterie**: Le polling consomme peu de batterie (5 sec entre les requêtes)
3. **WiFi/Données**: Le device doit avoir internet pour communiquer avec le backend
4. **Timeout**: Les commandes Android ont un timeout de 8 secondes

---

## Support

Pour les problèmes:
1. Vérifier les logs
2. Tester les commandes manuellement
3. Vérifier la connexion backend
4. Consulter les issues GitHub du projet

---

**Version:** 1.0  
**Dernière mise à jour:** 2026-04-21
