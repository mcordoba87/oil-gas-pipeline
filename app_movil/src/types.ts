export interface Dispositivo {
  id: number;
  device_id: string;
  operador: string | null;
  plataforma: string;
  activo: boolean;
  created_at: string;
  last_seen: string;
}

export interface Notificacion {
  id: number;
  time: string;
  pozo_id: string;
  tipo: string;
  severidad: string;
  mensaje: string | null;
  canal: string;
  leida: boolean;
}

export interface Pozo {
  pozo_id: string;
  cuenca: string | null;
  estado_actual: string | null;
}

export interface Lectura {
  time: string;
  pozo_id: string;
  presion_psi: number;
  temperatura_c: number;
  caudal_bpd: number;
  gas_mcfd: number;
}

export interface AppConfig {
  baseUrl: string;
  mqttUrl: string;
  apiKey: string;
  operador: string;
  deviceId: string;
}
