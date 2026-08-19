import type { Lectura, Notificacion, Pozo } from './types';

const CONTENT_JSON = { 'Content-Type': 'application/json' };

function headers(apiKey: string): Record<string, string> {
  return { ...CONTENT_JSON, 'X-API-Key': apiKey };
}

async function request<T>(
  baseUrl: string,
  apiKey: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { ...headers(apiKey), ...(options.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} en ${path}`);
  }
  return (await res.json()) as T;
}

export async function registrarDispositivo(
  baseUrl: string,
  apiKey: string,
  operador: string,
  deviceId: string,
  plataforma = 'android',
): Promise<void> {
  await request(baseUrl, apiKey, '/dispositivos', {
    method: 'POST',
    body: JSON.stringify({ operador, device_id: deviceId, plataforma }),
  });
}

export async function fetchPozos(baseUrl: string, apiKey: string): Promise<Pozo[]> {
  const data = await request<{ pozos: Pozo[] }>(baseUrl, apiKey, '/pozos');
  return data.pozos;
}

export async function fetchLecturas(
  baseUrl: string,
  apiKey: string,
  pozoId: string,
  limit = 50,
): Promise<Lectura[]> {
  const data = await request<{ lecturas: Lectura[] }>(
    baseUrl,
    apiKey,
    `/pozos/${encodeURIComponent(pozoId)}/lecturas?limit=${limit}`,
  );
  return data.lecturas;
}

export async function fetchInbox(
  baseUrl: string,
  apiKey: string,
  deviceId: string,
  leida: 'todas' | 'no_leidas' | 'leidas' = 'todas',
): Promise<Notificacion[]> {
  const data = await request<{ notificaciones: Notificacion[] }>(
    baseUrl,
    apiKey,
    `/dispositivos/${encodeURIComponent(deviceId)}/notificaciones?leida=${leida}`,
  );
  return data.notificaciones;
}

export async function marcarLeida(
  baseUrl: string,
  apiKey: string,
  notificacionId: number,
): Promise<void> {
  await request(baseUrl, apiKey, `/notificaciones/${notificacionId}/leida`, {
    method: 'POST',
  });
}
