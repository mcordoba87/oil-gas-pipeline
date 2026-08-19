/**
 * App móvil de campo (roadmap Fase 4, item 4.4).
 * Pantallas: Login -> Dashboard de pozos -> Detalle de pozo / Notificaciones.
 * Push en tiempo real: MQTT sobre WebSocket (topic notificaciones/{device_id})
 * + inbox REST contra el backend api/campo_app_api.py.
 * @format
 */

import React, { useEffect, useMemo, useState } from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { loadConfig } from './src/config';
import { connectPush, disconnectPush } from './src/mqtt';
import type { AppConfig, Notificacion } from './src/types';

import DashboardScreen from './src/screens/DashboardScreen';
import LoginScreen from './src/screens/LoginScreen';
import NotificationsScreen from './src/screens/NotificationsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import WellDetailScreen from './src/screens/WellDetailScreen';

type ScreenName = 'login' | 'dashboard' | 'notifications' | 'well' | 'settings';

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [screen, setScreen] = useState<ScreenName>('login');
  const [selectedWell, setSelectedWell] = useState<string | null>(null);
  const [realtime, setRealtime] = useState<Notificacion[]>([]);

  useEffect(() => {
    loadConfig().then(setConfig);
  }, []);

  // Conexión MQTT para push en vivo cuando hay device_id (ya registrado).
  useEffect(() => {
    if (!config || !config.deviceId) {
      return;
    }
    connectPush(config.mqttUrl, config.deviceId, notif => {
      setRealtime(prev => [notif, ...prev.filter(n => n.id !== notif.id)].slice(0, 200));
    });
    return () => disconnectPush();
  }, [config, config?.deviceId]);

  const unread = useMemo(
    () => realtime.filter(n => !n.leida).length,
    [realtime],
  );

  if (!config) {
    return null; // cargando configuración guardada
  }

  const goBack = () => setScreen(screen === 'notifications' || screen === 'well' ? 'dashboard' : 'login');

  const onLogin = (next: AppConfig) => {
    setConfig(next);
    setScreen('dashboard');
  };

  const markRead = (id: number) => {
    setRealtime(prev => prev.map(n => (n.id === id ? { ...n, leida: true } : n)));
  };

  return (
    <SafeAreaProvider>
      <StatusBar barStyle="light-content" />
      {screen === 'login' && (
        <LoginScreen
          config={config}
          onLogin={onLogin}
          onSettings={() => setScreen('settings')}
        />
      )}
      {screen === 'dashboard' && (
        <DashboardScreen
          config={config}
          unread={unread}
          onOpenNotifications={() => setScreen('notifications')}
          onOpenSettings={() => setScreen('settings')}
          onSelectWell={pozoId => {
            setSelectedWell(pozoId);
            setScreen('well');
          }}
        />
      )}
      {screen === 'well' && selectedWell && (
        <WellDetailScreen
          config={config}
          pozoId={selectedWell}
          onBack={goBack}
        />
      )}
      {screen === 'notifications' && (
        <NotificationsScreen
          config={config}
          notificaciones={realtime}
          onMarkRead={markRead}
          onBack={goBack}
        />
      )}
      {screen === 'settings' && (
        <SettingsScreen
          config={config}
          onSave={next => {
            setConfig(next);
            setScreen('dashboard');
          }}
          onBack={goBack}
        />
      )}
    </SafeAreaProvider>
  );
}

export default App;