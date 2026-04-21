"""
Router pour gérer la communication avec les appareils Termux
(simulation d'objets IoT sur téléphones mobiles)

Stockage simple : utilise things_collection avec type="termux_device" et type="pending_command"
Pas de collections séparées = moins de complexité
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import uuid4

from ..base import things_collection

termux_router = APIRouter(tags=["termux"])


class TermuxDeviceRegister(BaseModel):
    """Modèle d'enregistrement d'un appareil Termux"""
    device_id: str
    device_name: str
    phone_model: str
    android_version: str
    ip_address: Optional[str] = None
    port: Optional[int] = None


class TermuxDeviceStatus(BaseModel):
    """Modèle de statut d'appareil Termux"""
    device_id: str
    battery: int  # 0-100
    connection_status: str  # "connected", "disconnected"
    uptime_seconds: int
    objects_simulated: list[dict]  # Liste des objets simulés
    metadata: Optional[dict] = None


class TermuxCommand(BaseModel):
    """Modèle de commande pour Termux"""
    action: str  # "play", "mute", "volume_up", etc.
    object_id: str  # ID de l'objet à contrôler (p.ex "tv_1")
    parameters: dict  # Paramètres spécifiques à l'action


@termux_router.post("/termux/register")
def register_termux_device(device: TermuxDeviceRegister = Body(...)):
    """
    Enregistre un nouveau appareil Termux auprès du système.
    
    Crée un document type="termux_device" dans things_collection.
    """
    try:
        device_data = {
            "id": device.device_id,
            "type": "termux_device",
            "device_id": device.device_id,
            "device_name": device.device_name,
            "phone_model": device.phone_model,
            "android_version": device.android_version,
            "ip_address": device.ip_address,
            "port": device.port,
            "registered_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
            "status": "online",
            "objects_simulated": []
        }
        
        result = things_collection.update_one(
            {"id": device.device_id, "type": "termux_device"},
            {"$set": device_data},
            upsert=True
        )
        
        return {
            "success": True,
            "device_id": device.device_id,
            "message": f"Appareil {device.device_name} enregistré avec succès",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement: {str(e)}")


@termux_router.get("/termux/{device_id}/commands")
def get_pending_commands(device_id: str):
    """
    Récupère les commandes en attente pour un appareil Termux.
    
    Termux appelle cet endpoint régulièrement (polling) pour récupérer
    les commandes que le frontend a envoyées.
    
    Réponse:
    - commands: liste des commandes en attente (type="pending_command")
    - device_status: infos du device mises à jour
    """
    try:
        # Récupérer l'appareil
        device = things_collection.find_one({"id": device_id, "type": "termux_device"})
        if not device:
            raise HTTPException(status_code=404, detail=f"Appareil {device_id} non trouvé")
        
        # Mettre à jour le heartbeat
        things_collection.update_one(
            {"id": device_id, "type": "termux_device"},
            {"$set": {
                "last_heartbeat": datetime.utcnow().isoformat(),
                "status": "online"
            }}
        )
        
        # Récupérer les commandes en attente
        commands = list(things_collection.find({
            "device_id": device_id,
            "type": "pending_command",
            "executed": False
        }).sort("created_at", 1).limit(50))
        
        # Nettoyer les _id MongoDB
        for cmd in commands:
            if "_id" in cmd:
                cmd["_id"] = str(cmd["_id"])
        
        return {
            "device_id": device_id,
            "commands": commands,
            "device_status": {
                "status": device.get("status", "unknown"),
                "last_heartbeat": device.get("last_heartbeat"),
                "battery": device.get("battery", -1),
                "registered_at": device.get("registered_at")
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération commandes: {str(e)}")


@termux_router.post("/termux/{device_id}/status")
def update_termux_status(device_id: str, status: TermuxDeviceStatus = Body(...)):
    """
    Met à jour le statut d'un appareil Termux.
    
    Termux appelle cet endpoint régulièrement pour envoyer son état
    (batterie, statut de connexion, objets simulés, etc.)
    """
    try:
        status_data = {
            "id": device_id,
            "type": "termux_device",
            "device_id": device_id,
            "battery": status.battery,
            "connection_status": status.connection_status,
            "uptime_seconds": status.uptime_seconds,
            "objects_simulated": status.objects_simulated,
            "metadata": status.metadata or {},
            "last_update": datetime.utcnow().isoformat(),
            "status": "online" if status.connection_status == "connected" else "offline"
        }
        
        result = things_collection.update_one(
            {"id": device_id, "type": "termux_device"},
            {"$set": status_data},
            upsert=False
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Appareil {device_id} non trouvé")
        
        return {
            "success": True,
            "device_id": device_id,
            "message": "Statut mis à jour avec succès",
            "battery": status.battery,
            "status": "online" if status.connection_status == "connected" else "offline",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur mise à jour statut: {str(e)}")


@termux_router.get("/termux/devices/all")
def get_all_termux_devices():
    """
    Liste tous les appareils Termux enregistrés (admin endpoint).
    """
    try:
        devices = list(things_collection.find({"type": "termux_device"}).sort("last_heartbeat", -1))
        
        # Nettoyer les _id
        for device in devices:
            if "_id" in device:
                device["_id"] = str(device["_id"])
        
        return {
            "count": len(devices),
            "devices": devices,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur récupération appareils: {str(e)}")


@termux_router.post("/termux/{device_id}/send-command")
def send_command_to_device(device_id: str, command: TermuxCommand = Body(...)):
    """
    Envoie une commande à un appareil Termux.
    
    Le frontend appelle cet endpoint pour envoyer des commandes à Termux.
    Termux les récupère via GET /termux/{device_id}/commands
    """
    try:
        # Vérifier que l'appareil existe
        device = things_collection.find_one({"id": device_id, "type": "termux_device"})
        if not device:
            raise HTTPException(status_code=404, detail=f"Appareil {device_id} non trouvé")
        
        # Créer la commande
        command_id = str(uuid4())
        command_data = {
            "id": command_id,
            "type": "pending_command",
            "command_id": command_id,
            "device_id": device_id,
            "action": command.action,
            "object_id": command.object_id,
            "parameters": command.parameters,
            "created_at": datetime.utcnow().isoformat(),
            "executed": False,
            "fetched_at": None,
            "executed_at": None
        }
        
        result = things_collection.insert_one(command_data)
        
        return {
            "success": True,
            "command_id": command_id,
            "device_id": device_id,
            "message": "Commande envoyée avec succès",
            "action": command.action,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur envoi commande: {str(e)}")
