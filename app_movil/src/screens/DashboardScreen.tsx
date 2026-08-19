import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { fetchLecturas, fetchPozos } from '../api';
import { colors } from '../theme';
import type { AppConfig, Lectura, Pozo } from '../types';
import Screen from '../components/Screen';

interface WellRow {
  pozo: Pozo;
  lectura: Lectura | null;
}

interface Props {
  config: AppConfig;
  unread: number;
  onOpenNotifications: () => void;
  onOpenSettings: () => void;
  onSelectWell: (pozoId: string) => void;
}

export default function DashboardScreen({
  config,
  unread,
  onOpenNotifications,
  onOpenSettings,
  onSelectWell,
}: Props) {
  const [rows, setRows] = useState<WellRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const pozos = await fetchPozos(config.baseUrl, config.apiKey);
      const next: WellRow[] = [];
      for (const pozo of pozos) {
        let lectura: Lectura | null = null;
        try {
          const lecturas = await fetchLecturas(config.baseUrl, config.apiKey, pozo.pozo_id, 1);
          lectura = lecturas[0] ?? null;
        } catch {
          lectura = null;
        }
        next.push({ pozo, lectura });
      }
      setRows(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [config]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Screen
      title="Pozos en campo"
      subtitle={config.operador || 'operador'}
      onRight={onOpenNotifications}
      rightLabel={`🔔${unread > 0 ? ` ${unread}` : ''}`}
    >
      {loading ? (
        <ActivityIndicator color={colors.primary} style={styles.spinner} size="large" />
      ) : error ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retry} onPress={() => { setLoading(true); load(); }}>
            <Text style={styles.retryText}>Reintentar</Text>
          </Pressable>
        </View>
      ) : (
        <ScrollView
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
              tintColor={colors.primary}
            />
          }
          contentContainerStyle={styles.content}
        >
          {rows.map(({ pozo, lectura }) => (
            <Pressable key={pozo.pozo_id} style={styles.card} onPress={() => onSelectWell(pozo.pozo_id)}>
              <View style={styles.cardHeader}>
                <Text style={styles.wellName}>{pozo.pozo_id}</Text>
                <Text style={styles.wellEstado}>{pozo.estado_actual ?? '—'}</Text>
              </View>
              {lectura ? (
                <View style={styles.metrics}>
                  <Metric label="Presión" value={format(lectura.presion_psi, 'psi')} accent={presionColor(lectura.presion_psi)} />
                  <Metric label="Caudal" value={format(lectura.caudal_bpd, 'BPD')} />
                  <Metric label="Temp" value={format(lectura.temperatura_c, '°C')} />
                  <Metric label="Gas" value={format(lectura.gas_mcfd, 'mcfd')} />
                </View>
              ) : (
                <Text style={styles.noReadings}>Sin lecturas recientes</Text>
              )}
              <Text style={styles.wellTime}>
                {lectura ? new Date(lectura.time).toLocaleTimeString() : ''}
              </Text>
            </Pressable>
          ))}
          <Pressable style={styles.settingsBtn} onPress={onOpenSettings}>
            <Text style={styles.settingsText}>⚙️ Ajustes de conexión</Text>
          </Pressable>
        </ScrollView>
      )}
    </Screen>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, accent ? { color: accent } : null]}>{value}</Text>
    </View>
  );
}

function format(value: number, unit: string): string {
  return `${value.toFixed(1)} ${unit}`;
}

function presionColor(presion: number): string {
  if (presion > 2000) return colors.danger;
  if (presion > 1500) return colors.warning;
  return colors.success;
}

const styles = StyleSheet.create({
  spinner: { marginTop: 40 },
  content: { padding: 12, gap: 12 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 12 },
  errorText: { color: colors.danger, textAlign: 'center' },
  retry: { backgroundColor: colors.primary, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 10 },
  retryText: { color: colors.background, fontWeight: '700' },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  wellName: { color: colors.text, fontSize: 16, fontWeight: '700' },
  wellEstado: { color: colors.textMuted, fontSize: 13 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  metric: { flexBasis: '45%', gap: 2 },
  metricLabel: { color: colors.textMuted, fontSize: 11, textTransform: 'uppercase' },
  metricValue: { color: colors.text, fontSize: 16, fontWeight: '600' },
  noReadings: { color: colors.textMuted, fontSize: 13 },
  wellTime: { color: colors.textMuted, fontSize: 11, marginTop: 8 },
  settingsBtn: {
    backgroundColor: colors.surfaceAlt,
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  settingsText: { color: colors.primary, fontSize: 14, fontWeight: '600' },
});