/**
 * Client Termux - Utilitaire pour communiquer avec les appareils Termux
 * Permet au frontend de contrôler les objets simulés sur les téléphones
 */

class TermuxClient {
  constructor(apiBase = null) {
    this.apiBase = apiBase || window.APP_CONFIG?.API_BASE || "http://127.0.0.1:8000";
    this.pollInterval = 5000; // 5 secondes
    this.pollTimers = new Map();
  }

  /**
   * Enregistre un nouveau appareil Termux
   */
  async registerDevice(deviceId, deviceName, phoneModel, androidVersion, ipAddress = null, port = null) {
    try {
      const response = await fetch(`${this.apiBase}/termux/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_id: deviceId,
          device_name: deviceName,
          phone_model: phoneModel,
          android_version: androidVersion,
          ip_address: ipAddress,
          port: port
        })
      });

      if (!response.ok) throw new Error(`Erreur ${response.status}`);
      const data = await response.json();
      
      console.log(`✅ Appareil ${deviceName} enregistré:`, data);
      return data;
    } catch (error) {
      console.error("❌ Erreur enregistrement:", error);
      throw error;
    }
  }

  /**
   * Récupère les commandes en attente pour un appareil
   */
  async getCommands(deviceId) {
    try {
      const response = await fetch(`${this.apiBase}/termux/${deviceId}/commands`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });

      if (!response.ok) throw new Error(`Erreur ${response.status}`);
      const data = await response.json();
      
      if (data.commands && data.commands.length > 0) {
        console.log(`📬 ${data.commands.length} commande(s) pour ${deviceId}`);
      }
      
      return data;
    } catch (error) {
      console.error("❌ Erreur récupération commandes:", error);
      throw error;
    }
  }

  /**
   * Met à jour le statut d'un appareil
   */
  async updateStatus(deviceId, battery, connectionStatus, uptimeSeconds, objectsSimulated, metadata = null) {
    try {
      const response = await fetch(`${this.apiBase}/termux/${deviceId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_id: deviceId,
          battery: battery,
          connection_status: connectionStatus,
          uptime_seconds: uptimeSeconds,
          objects_simulated: objectsSimulated,
          metadata: metadata || {}
        })
      });

      if (!response.ok) throw new Error(`Erreur ${response.status}`);
      const data = await response.json();
      
      return data;
    } catch (error) {
      console.error("❌ Erreur mise à jour statut:", error);
      throw error;
    }
  }

  /**
   * Envoie une commande à un appareil (depuis le frontend)
   */
  async sendCommand(deviceId, commandId, action, objectId, parameters) {
    try {
      const response = await fetch(`${this.apiBase}/termux/${deviceId}/send-command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command_id: commandId,
          action: action,
          object_id: objectId,
          parameters: parameters,
          timestamp: new Date().toISOString()
        })
      });

      if (!response.ok) throw new Error(`Erreur ${response.status}`);
      const data = await response.json();
      
      console.log(`📤 Commande envoyée à ${deviceId}:`, data);
      return data;
    } catch (error) {
      console.error("❌ Erreur envoi commande:", error);
      throw error;
    }
  }

  /**
   * Récupère tous les appareils Termux enregistrés
   */
  async getAllDevices() {
    try {
      const response = await fetch(`${this.apiBase}/termux/devices/all`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });

      if (!response.ok) throw new Error(`Erreur ${response.status}`);
      const data = await response.json();
      
      console.log(`📱 ${data.count} appareil(s) trouvé(s)`);
      return data;
    } catch (error) {
      console.error("❌ Erreur récupération appareils:", error);
      throw error;
    }
  }

  /**
   * Démarre le polling des commandes pour un appareil
   * Appelle une callback chaque fois que de nouvelles commandes arrivent
   */
  startPolling(deviceId, onCommandsReceived) {
    if (this.pollTimers.has(deviceId)) {
      console.warn(`⚠️ Polling déjà actif pour ${deviceId}`);
      return;
    }

    const poll = async () => {
      try {
        const data = await this.getCommands(deviceId);
        if (data.commands && data.commands.length > 0 && onCommandsReceived) {
          onCommandsReceived(data.commands);
        }
      } catch (error) {
        console.error(`Erreur polling ${deviceId}:`, error);
      }
      
      // Programmer le prochain poll
      const timer = setTimeout(poll, this.pollInterval);
      this.pollTimers.set(deviceId, timer);
    };

    // Démarrer le premier poll
    console.log(`🔄 Polling démarré pour ${deviceId} (interval: ${this.pollInterval}ms)`);
    poll();
  }

  /**
   * Arrête le polling pour un appareil
   */
  stopPolling(deviceId) {
    if (this.pollTimers.has(deviceId)) {
      clearTimeout(this.pollTimers.get(deviceId));
      this.pollTimers.delete(deviceId);
      console.log(`⏹️ Polling arrêté pour ${deviceId}`);
    }
  }

  /**
   * Arrête le polling pour tous les appareils
   */
  stopAllPolling() {
    this.pollTimers.forEach((timer, deviceId) => {
      clearTimeout(timer);
      console.log(`⏹️ Polling arrêté pour ${deviceId}`);
    });
    this.pollTimers.clear();
  }
}

// Créer une instance globale
window.termuxClient = new TermuxClient(window.APP_CONFIG?.API_BASE);

// Export pour Node.js (si utilisé dans un contexte Node)
if (typeof module !== "undefined" && module.exports) {
  module.exports = TermuxClient;
}
