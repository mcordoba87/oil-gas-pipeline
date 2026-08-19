import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { registrarDispositivo } from '../api';
import { saveConfig } from '../config';
import { colors } from '../theme';
import type { AppConfig } from '../types';
import Screen from '../components/Screen';

interface Props {
  config: AppConfig;
  onLogin: (config: AppConfig) => void;
  onSettings: () => void;
}

export default function LoginScreen({ config, onLogin, onSettings }: Props) {
  const [operador, setOperador] = useState(config.operador);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = async () => {
    if (!operador.trim()) {
      setError('Ingresá tu nombre de operador.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const deviceId =
        config.deviceId || `campo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
      await registrarDispositivo(
        config.baseUrl,
        config.apiKey,
        operador.trim(),
        deviceId,
        'android',
      );
      await saveConfig({ ...config, operador: operador.trim(), deviceId });
      onLogin({ ...config, operador: operador.trim(), deviceId });
    } catch (err) {
      setError(`No se pudo registrar: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen title="Campo O&G" subtitle="App móvil de campo">
      <View style={styles.body}>
        <Text style={styles.logo}>🛢️</Text>
        <Text style={styles.title}>Operador de campo</Text>
        <Text style={styles.subtitle}>
          Ingresá tu nombre para registrar este dispositivo y recibir alertas de
          presión en tiempo real.
        </Text>

        <TextInput
          style={styles.input}
          value={operador}
          onChangeText={setOperador}
          placeholder="Nombre del operador"
          placeholderTextColor={colors.textMuted}
          autoCapitalize="words"
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable style={styles.button} onPress={login} disabled={loading}>
          {loading ? (
            <ActivityIndicator color={colors.background} />
          ) : (
            <Text style={styles.buttonText}>Entrar</Text>
          )}
        </Pressable>

        <Pressable onPress={onSettings} hitSlop={12}>
          <Text style={styles.settingsLink}>Ajustes de conexión</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1, padding: 24, justifyContent: 'center', gap: 8 },
  logo: { fontSize: 44, textAlign: 'center' },
  title: { color: colors.text, fontSize: 22, fontWeight: '700', textAlign: 'center' },
  subtitle: { color: colors.textMuted, fontSize: 14, textAlign: 'center', marginBottom: 16 },
  input: {
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 15,
  },
  error: { color: colors.danger, fontSize: 13, textAlign: 'center' },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: { color: colors.background, fontSize: 16, fontWeight: '700' },
  settingsLink: { color: colors.primary, textAlign: 'center', marginTop: 16 },
});