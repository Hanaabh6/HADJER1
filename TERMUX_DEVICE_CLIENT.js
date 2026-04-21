/**
 * Termux IoT Device Client
 * Lance un serveur local + se connecte au backend pour recevoir les commandes
 * 
 * Installation sur Termux:
 * 1. pkg install nodejs
 * 2. mkdir -p ~/intellibuild && cd ~/intellibuild
 * 3. npm init -y
 * 4. npm install axios
 * 5. Copier ce fichier en tant que device-client.js
 * 6. node device-client.js
 * 
 * Configuration:
 * - Modifier BACKEND_URL en bas pour pointer vers ton backend hébergé
 * - Modifier DEVICE_ID et DEVICE_NAME
 */

const http = require("http");
const { execFile } = require("child_process");
const { promisify } = require("util");
const axios = require("axios");

const execFileAsync = promisify(execFile);

// ========== CONFIG ==========
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000"; // À modifier avec ton URL Railway/Render
const DEVICE_ID = process.env.DEVICE_ID || "termux_tv_1";
const DEVICE_NAME = process.env.DEVICE_NAME || "Smart TV Termux";
const PHONE_MODEL = process.env.PHONE_MODEL || "Android Phone";
const ANDROID_VERSION = process.env.ANDROID_VERSION || "12";
const LOCAL_PORT = process.env.LOCAL_PORT || 3001;
const POLL_INTERVAL = process.env.POLL_INTERVAL || 5000; // 5 secondes

// ========== STATE ==========
let power = "off";
let currentVolume = 10;
let muted = false;
let currentChannel = 0;
let isRegistered = false;
let pollInterval = null;

const channels = [
  { slug: "tf1", label: "TF1", file: "tf1.mp4" },
  { slug: "natgeo", label: "National Geographic", file: "natgeo.mp4" },
  { slug: "arte", label: "ARTE", file: "arte.mp4" },
  { slug: "france24", label: "France 24", file: "france24.mp4" }
];

// ========== ANDROID COMMANDS ==========
async function runCommand(command, args = []) {
  try {
    const result = await execFileAsync(command, args, { timeout: 8000, windowsHide: true });
    return {
      ok: true,
      stdout: String(result.stdout || "").trim(),
      stderr: String(result.stderr || "").trim()
    };
  } catch (error) {
    return {
      ok: false,
      stdout: String(error.stdout || "").trim(),
      stderr: String(error.stderr || error.message || "").trim(),
      code: error.code
    };
  }
}

async function tvOn() {
  await runCommand("input", ["keyevent", "224"]); // wakeup
  await runCommand("input", ["keyevent", "82"]); // unlock/menu
  power = "on";
  console.log("✅ TV allumée");
  return { ok: true, power };
}

async function tvOff() {
  await runCommand("input", ["keyevent", "4"]); // back
  await runCommand("input", ["keyevent", "3"]); // home
  await runCommand("input", ["keyevent", "223"]); // sleep
  power = "off";
  console.log("✅ TV éteinte");
  return { ok: true, power };
}

async function applyVolume(level) {
  const safeLevel = Math.max(0, Math.min(25, Number(level) || 0));
  const target = safeLevel > currentVolume ? 24 : 25; // 24=vol up, 25=vol down
  const steps = Math.abs(safeLevel - currentVolume);

  for (let i = 0; i < steps; i++) {
    await runCommand("input", ["keyevent", String(target)]);
  }

  muted = safeLevel === 0;
  currentVolume = safeLevel;
  console.log(`🔊 Volume: ${safeLevel}`);
  return { ok: true, volume: safeLevel };
}

async function launchChannel(index) {
  if (index < 0 || index >= channels.length) {
    return { ok: false, error: "Channel not found" };
  }

  if (power !== "on") {
    await tvOn();
  }

  currentChannel = index;
  const channel = channels[currentChannel];
  const path = `/storage/emulated/0/Download/${channel.file}`;

  const result = await runCommand("am", [
    "start",
    "-a",
    "android.intent.action.VIEW",
    "-d",
    `file://${path}`,
    "-t",
    "video/mp4"
  ]);

  if (!result.ok) {
    console.error("❌ Erreur lancement vidéo:", result.stderr);
    return { ok: false, error: result.stderr };
  }

  console.log(`📺 Chaîne lancée: ${channel.label}`);
  return { ok: true, channel: channel.label, file: channel.file };
}

// ========== BACKEND API CALLS ==========
async function registerDevice() {
  try {
    console.log(`📱 Enregistrement du device auprès de ${BACKEND_URL}...`);
    
    const response = await axios.post(`${BACKEND_URL}/termux/register`, {
      device_id: DEVICE_ID,
      device_name: DEVICE_NAME,
      phone_model: PHONE_MODEL,
      android_version: ANDROID_VERSION,
      ip_address: "127.0.0.1",
      port: LOCAL_PORT
    }, { timeout: 5000 });

    console.log("✅ Device enregistré:", response.data.message);
    isRegistered = true;
    return true;
  } catch (error) {
    console.error("❌ Erreur enregistrement:", error.message);
    return false;
  }
}

async function updateStatus() {
  if (!isRegistered) return;

  try {
    const response = await axios.post(`${BACKEND_URL}/termux/${DEVICE_ID}/status`, {
      device_id: DEVICE_ID,
      battery: 75, // À récupérer avec `termux-battery-status` si besoin
      connection_status: "connected",
      uptime_seconds: Math.floor(process.uptime()),
      objects_simulated: [
        {
          id: "tv_1",
          type: "television",
          status: power,
          channel: channels[currentChannel].label,
          volume: currentVolume,
          muted: muted
        }
      ],
      metadata: { local_port: LOCAL_PORT }
    }, { timeout: 5000 });

    // console.log("📤 Statut envoyé");
  } catch (error) {
    console.error("⚠️  Erreur envoi statut:", error.message);
  }
}

async function pollCommands() {
  if (!isRegistered) return;

  try {
    const response = await axios.get(`${BACKEND_URL}/termux/${DEVICE_ID}/commands`, {
      timeout: 5000
    });

    const { commands } = response.data;

    if (commands && commands.length > 0) {
      console.log(`📬 ${commands.length} commande(s) reçue(s)`);
      
      for (const cmd of commands) {
        await executeCommand(cmd);
      }
    }
  } catch (error) {
    console.error("⚠️  Erreur polling:", error.message);
  }
}

async function executeCommand(cmd) {
  const { command_id, action, parameters } = cmd;
  let result = { ok: false, error: "Action inconnue" };

  console.log(`⚡ Exécution: ${action}`);

  try {
    switch (action) {
      case "power_on":
        result = await tvOn();
        break;

      case "power_off":
        result = await tvOff();
        break;

      case "play_channel":
        const channelIndex = channels.findIndex(ch => 
          ch.slug === parameters.channel || ch.label === parameters.channel
        );
        if (channelIndex >= 0) {
          result = await launchChannel(channelIndex);
        } else {
          result = { ok: false, error: "Channel not found" };
        }
        break;

      case "next_channel":
        const nextIndex = (currentChannel + 1) % channels.length;
        result = await launchChannel(nextIndex);
        break;

      case "prev_channel":
        const prevIndex = (currentChannel - 1 + channels.length) % channels.length;
        result = await launchChannel(prevIndex);
        break;

      case "volume_up":
        result = await applyVolume(currentVolume + 1);
        break;

      case "volume_down":
        result = await applyVolume(currentVolume - 1);
        break;

      case "set_volume":
        result = await applyVolume(parameters.level || 10);
        break;

      case "mute":
        await applyVolume(0);
        result = { ok: true, muted: true };
        break;

      default:
        result = { ok: false, error: `Action inconnue: ${action}` };
    }

    if (result.ok) {
      console.log(`✅ ${action} réussi`);
    } else {
      console.error(`❌ ${action} échoué:`, result.error);
    }
  } catch (error) {
    console.error(`❌ Erreur exécution ${action}:`, error.message);
    result = { ok: false, error: error.message };
  }
}

// ========== LOCAL HTTP SERVER (OPTIONNEL) ==========
const server = http.createServer((req, res) => {
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url === "/health") {
    res.writeHead(200);
    res.end(JSON.stringify({
      ok: true,
      device_id: DEVICE_ID,
      power,
      volume: currentVolume,
      channel: channels[currentChannel].label,
      backend_connected: isRegistered,
      uptime: Math.floor(process.uptime())
    }));
    return;
  }

  if (req.url === "/status") {
    res.writeHead(200);
    res.end(JSON.stringify({
      power,
      volume: currentVolume,
      muted,
      channel: channels[currentChannel].label,
      battery: 75
    }));
    return;
  }

  res.writeHead(404);
  res.end(JSON.stringify({ error: "Not found" }));
});

// ========== STARTUP ==========
async function startup() {
  console.log("🚀 Démarrage du client Termux IoT...");
  console.log(`Backend URL: ${BACKEND_URL}`);
  console.log(`Device ID: ${DEVICE_ID}`);

  // Enregistrer le device
  let registrationAttempts = 0;
  while (!isRegistered && registrationAttempts < 5) {
    await registerDevice();
    if (!isRegistered) {
      registrationAttempts++;
      console.log(`⏳ Nouvelle tentative dans 3 secondes... (${registrationAttempts}/5)`);
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

  if (!isRegistered) {
    console.error("❌ Impossible de se connecter au backend. Vérifiez l'URL.");
    process.exit(1);
  }

  // Lancer le polling et le serveur local
  server.listen(LOCAL_PORT, "0.0.0.0", () => {
    console.log(`✅ Serveur local lancé sur 0.0.0.0:${LOCAL_PORT}`);
    console.log(`✅ Polling du backend tous les ${POLL_INTERVAL}ms`);
  });

  // Polling des commandes
  pollInterval = setInterval(async () => {
    await pollCommands();
    await updateStatus();
  }, POLL_INTERVAL);
}

// ========== GRACEFUL SHUTDOWN ==========
process.on("SIGINT", () => {
  console.log("\n👋 Arrêt du client...");
  if (pollInterval) clearInterval(pollInterval);
  server.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  console.log("\n👋 Arrêt du client (SIGTERM)...");
  if (pollInterval) clearInterval(pollInterval);
  server.close();
  process.exit(0);
});

// ========== RUN ==========
startup().catch(error => {
  console.error("Erreur au démarrage:", error);
  process.exit(1);
});
