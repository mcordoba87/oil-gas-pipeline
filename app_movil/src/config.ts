import AsyncStorage from '@react-native-async-storage/async-storage';

import type { AppConfig } from './types';

const STORAGE_KEY = 'campo_app_config_v1';

// IP LAN del PC donde corre docker-compose. Ajustar desde la pantalla de
// Ajustes de la app (ver .env -> CAMPO_APP_LAN_IP).
export const DEFAULT_CONFIG: AppConfig = {
  baseUrl: 'http://192.168.1.50:8010',
  mqttUrl: 'ws://192.168.1.50:9001',
  apiKey: '',
  operador: '',
  deviceId: '',
};

export async function loadConfig(): Promise<AppConfig> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (raw) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) };
    }
  } catch (err) {
    console.warn('No se pudo leer la configuración guardada', err);
  }
  return { ...DEFAULT_CONFIG };
}

export async function saveConfig(config: AppConfig): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export async function clearConfig(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
