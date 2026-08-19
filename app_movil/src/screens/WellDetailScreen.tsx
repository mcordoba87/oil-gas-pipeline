import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { fetchLecturas } from '../api';
import { colors } from '../theme';
import type { AppConfig, Lectura } from '../types';
import Screen from '../components/Screen';

interface Props {
  config: AppConfig;
  pozoId: string;
  onBack: () => void;
}

export default function WellDetailScreen({ config, pozoId, onBack }: Props) {
  const [lecturas, setLecturas] = useState<Lectura[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchLecturas(config.baseUrl, config.apiKey, pozoId, 50);
      setLecturas(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [config, pozoId]);

  useEffect(() => {
    load();
  }, [load]);

  const ultima = lecturas[0];

  return (
    <Screen title={pozoId} subtitle="Lecturas en vivo" onBack={onBack}>
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
        <FlatList
          data={lecturas}
          keyExtractor={item => item.time}
          ListHeaderComponent={
            ultima ? (
              <View style={styles.summary}>
                <SummaryItem label="Presión" value={`${ultima.presion_psi.toFixed(1)} psi`} />
                <SummaryItem label="Caudal" value={`${ultima.caudal_bpd.toFixed(1)} BPD`} />
                <SummaryItem label="Temp" value={`${ultima.temperatura_c.toFixed(1)} °C`} />
                <SummaryItem label="Gas" value={`${ultima.gas_mcfd.toFixed(1)} mcfd`} />
              </View>
            ) : (
              <View />
            )
          }
          contentContainerStyle={styles.content}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <Text style={styles.time}>{new Date(item.time).toLocaleString()}</Text>
              <Text style={styles.val}>{item.presion_psi.toFixed(1)} psi</Text>
              <Text style={styles.val}>{item.caudal_bpd.toFixed(1)} BPD</Text>
              <Text style={styles.val}>{item.temperatura_c.toFixed(1)} °C</Text>
            </View>
          )}
        />
      )}
    </Screen>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryItem}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  spinner: { marginTop: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, gap: 12 },
  errorText: { color: colors.danger, textAlign: 'center' },
  retry: { backgroundColor: colors.primary, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 10 },
  retryText: { color: colors.background, fontWeight: '700' },
  content: { padding: 12, gap: 8 },
  summary: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 8,
  },
  summaryItem: { flexBasis: '45%', gap: 2 },
  summaryLabel: { color: colors.textMuted, fontSize: 11, textTransform: 'uppercase' },
  summaryValue: { color: colors.text, fontSize: 16, fontWeight: '600' },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  time: { color: colors.textMuted, fontSize: 12, flex: 1.6 },
  val: { color: colors.text, fontSize: 13, flex: 1, textAlign: 'right' },
});