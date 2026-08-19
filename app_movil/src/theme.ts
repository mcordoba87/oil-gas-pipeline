export const colors = {
  background: '#0e1520',
  surface: '#16202f',
  surfaceAlt: '#1e2c3f',
  border: '#2a3a52',
  text: '#e6edf5',
  textMuted: '#8fa3bd',
  primary: '#f59e0b', // ámbar (llama de pozo)
  danger: '#ef4444',
  warning: '#f59e0b',
  info: '#38bdf8',
  success: '#22c55e',
  white: '#ffffff',
};

export const severidadColor = (severidad: string): string => {
  switch (severidad) {
    case 'critical':
      return colors.danger;
    case 'warning':
      return colors.warning;
    case 'info':
      return colors.info;
    default:
      return colors.textMuted;
  }
};