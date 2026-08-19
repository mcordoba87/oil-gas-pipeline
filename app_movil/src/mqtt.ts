import mqtt, { type MqttClient } from 'mqtt';

import type { Notificacion } from './types';

export interface PushHandler {
  (notificacion: Notificacion): void;
}

let client: MqttClient | null = null;

export function connectPush(mqttUrl: string, deviceId: string, onPush: PushHandler) {
  if (client) {
    client.end(true);
    client = null;
  }

  client = mqtt.connect(mqttUrl, {
    clientId: `campo-app-${deviceId}`,
    reconnectPeriod: 4000,
    connectTimeout: 10000,
    keepalive: 30,
    protocolVersion: 4,
  });

  client.on('connect', () => {
    client?.subscribe(`notificaciones/${deviceId}`, { qos: 1 });
  });

  client.on('message', (topic, payload) => {
    if (!topic.startsWith('notificaciones/')) {
      return;
    }
    try {
      const notif = JSON.parse(payload.toString()) as Notificacion;
      notif.leida = false;
      onPush(notif);
    } catch (err) {
      console.warn('Push MQTT inválido', err);
    }
  });

  client.on('error', err => {
    console.warn('Error MQTT', err);
  });

  return client;
}

export function disconnectPush() {
  if (client) {
    client.end(true);
    client = null;
  }
}
