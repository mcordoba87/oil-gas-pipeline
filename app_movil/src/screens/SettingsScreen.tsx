import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';

import { saveConfig } from '../config';
import { colors } from '../theme';
import type { AppConfig } from '../types';
import Screen from '../components/Screen';

interface Props {
  config: AppConfig;
  onSave: (config: AppConfig) => void;
  onBack: () => void;
}

export default function SettingsScreen({ config, onSave, onBack }: Props) {
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [mqttUrl, setMqttUrl] = useState(config.mqttUrl);
  const [apiKey, setApiKey] = useState(config.apiKey);

  const save = async () => {
    const next = { ...config, baseUrl, mqttUrl, apiKey };
    await saveConfig(next);
    onSave(next);
  };

  return (
    <Screen title="Ajustes" subtitle="Conexión al backend de campo" onBack={onBack}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.kav}
      >
        <ScrollView style={styles.body} contentContainerStyle={styles.content}>
          <Text style={styles.label}>URL API (REST) — puerto {':8010'}</Text>
          <TextInput
            style={styles.input}
            value={baseUrl}
            onChangeText={setBaseUrl}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="http://192.168.1.50:8010"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={styles.label}>URL MQTT (WebSocket) — puerto 9001</Text>
          <TextInput
            style={styles.input}
            value={mqttUrl}
            onChangeText={setMqttUrl}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="ws://192.168.1.50:9001"
            placeholderTextColor={colors.textMuted}
          />

          <Text style={styles.label}>API Key</Text>
          <TextInput
            style={styles.input}
            value={apiKey}
            onChangeText={setApiKey}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="X-API-Key"
            placeholderTextColor={colors.textMuted}
          />

          <Pressable style={styles.button} onPress={save}>
            <Text style={styles.buttonText}>Guardar</Text>
          </Pressable>

          <Text style={styles.hint}>
            El teléfono debe estar en la misma red Wi-Fi que el PC. La IP LAN se
            define en .env (CAMPO_APP_LAN_IP).
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  kav: { flex: 1 },
  body: { flex: 1 },
  content: { padding: 20, gap: 8 },
  label: { color: colors.textMuted, fontSize: 13, marginTop: 12 },
  input: {
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 20,
  },
  buttonText: { color: colors.background, fontSize: 16, fontWeight: '700' },
  hint: { color: colors.textMuted, fontSize: 12, marginTop: 16, lineHeight: 18 },
});