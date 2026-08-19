import React from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors } from '../theme';

interface Props {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  onRight?: () => void;
  rightLabel?: string;
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
}

export default function Screen({
  title,
  subtitle,
  onBack,
  onRight,
  rightLabel,
  children,
  style,
}: Props) {
  return (
    <SafeAreaView style={[styles.safe, style]} edges={['top', 'left', 'right']}>
      <View style={styles.header}>
        <View style={styles.headerSide}>
          {onBack ? (
            <Pressable onPress={onBack} hitSlop={12}>
              <Text style={styles.back}>←</Text>
            </Pressable>
          ) : null}
        </View>
        <View style={styles.headerTitle}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <View style={styles.headerSide}>
          {onRight && rightLabel ? (
            <Pressable onPress={onRight} hitSlop={12}>
              <Text style={styles.right}>{rightLabel}</Text>
            </Pressable>
          ) : null}
        </View>
      </View>
      <View style={styles.body}>{children}</View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  headerSide: { width: 56 },
  headerTitle: { flex: 1, alignItems: 'center' },
  title: { color: colors.text, fontSize: 18, fontWeight: '700' },
  subtitle: { color: colors.textMuted, fontSize: 12, marginTop: 2 },
  back: { color: colors.primary, fontSize: 22 },
  right: { color: colors.primary, fontSize: 14, fontWeight: '600' },
  body: { flex: 1 },
});