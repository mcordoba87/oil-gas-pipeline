import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { fetchInbox, marcarLeida } from '../api';
import { colors, severidadColor } from '../theme';
import type { AppConfig, Notificacion } from '../types';
import Screen from '../components/Screen';

interface Props {
  config: AppConfig;
  notificaciones: Notificacion[]; // inbox local (REST + push MQTT en tiempo real)
  onMarkRead: (id: number) => void;
  onBack: () => void;
}

export default function NotificationsScreen({ config, notificaciones, onMarkRead, onBack }: Props) {
  const [synced, setSynced] = useState<Notificacion[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchInbox(config.baseUrl, config.apiKey, config.deviceId, 'todas');
      setSynced(data);
    } catch (err) {
      console.warn('No se pudo sincronizar el inbox', err);
    } finally {
      setLoading(false);
    }
  }, [config]);

  useEffect(() => {
    load();
  }, [load]);

  // Fusiona el inbox sincronizado con los pushes MQTT en tiempo real
  // (los del push entran primero, sin duplicados por id).
  const all: Notificacion[] = useMemoMerge(synced, notificaciones);

  const read = async (id: number) => {
    onMarkRead(id);
    try {
      await marcarLeida(config.baseUrl, config.apiKey, id);
    } catch (err) {
      console.warn('No se pudo marcar como leída', err);
    }
  };

  return (
    <Screen title="Notificaciones" subtitle={config.operador || 'operador'} onBack={onBack}>
      {loading ? (
        <ActivityIndicator color={colors.primary} style={styles.spinner} size="large" />
      ) : (
        <FlatList
          data={all}
          keyExtractor={item => String(item.id)}
          contentContainerStyle={styles.content}
          ListEmptyComponent={<Text style={styles.empty}>Sin notificaciones</Text>}
          renderItem={({ item }) => (
            <Pressable style={[styles.card, item.leida ? styles.cardLeida : null]} onPress={() => read(item.id)}>
              <View style={styles.cardHeader}>
                <View style={[styles.badge, { backgroundColor: severidadColor(item.severidad) }]}>
                  <Text style={styles.badgeText}>{item.severidad.toUpperCase()}</Text>
                </View>
                <Text style={styles.time}>{new Date(item.time).toLocaleString()}</Text>
              </View>
              <Text style={styles.pozo}>{item.pozo_id}</Text>
              <Text style={styles.mensaje}>{item.mensaje ?? item.tipo}</Text>
              <View style={styles.cardFooter}>
                <Text style={styles.tipo}>{item.tipo} · {item.canal}</Text>
                {!item.leida ? <Text style={styles.nueva}>● nueva</Text> : null}
              </View>
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

function useMemoMerge(synced: Notificacion[], realtime: Notificacion[]): Notificacion[] {
  const seen = new Set<number>();
  const merged: Notificacion[] = [];
  for (const n of [...realtime, ...synced]) {
    if (!seen.has(n.id)) {
      seen.add(n.id);
      merged.push(n);
    }
  }
  return merged;
}

const styles = StyleSheet.create({
  spinner: { marginTop: 40 },
  content: { padding: 12, gap: 10 },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 40 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
  },
  cardLeida: { opacity: 0.55 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { color: colors.background, fontSize: 11, fontWeight: '700' },
  time: { color: colors.textMuted, fontSize: 11 },
  pozo: { color: colors.text, fontSize: 16, fontWeight: '700', marginTop: 8 },
  mensaje: { color: colors.text, fontSize: 14, marginTop: 2 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  tipo: { color: colors.textMuted, fontSize: 11 },
  nueva: { color: colors.primary, fontSize: 11, fontWeight: '700' },
});