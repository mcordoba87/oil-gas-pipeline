/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import AsyncStorage from '@react-native-async-storage/async-storage';
import App from '../App';

jest.mock('@react-native-async-storage/async-storage', () => {
  const store: Record<string, string> = {};
  return {
    __esModule: true,
    default: {
      getItem: jest.fn((key: string) => Promise.resolve(store[key] ?? null)),
      setItem: jest.fn((key: string, value: string) => {
        store[key] = value;
        return Promise.resolve();
      }),
      removeItem: jest.fn((key: string) => {
        delete store[key];
        return Promise.resolve();
      }),
      clear: jest.fn(() => {
        Object.keys(store).forEach(k => delete store[k]);
        return Promise.resolve();
      }),
    },
  };
});

// mqtt.js expone build ESM que jest no parsea; mock para el render test.
jest.mock('mqtt', () => {
  const fakeClient = () => ({
    end: jest.fn(),
    on: jest.fn(),
    subscribe: jest.fn(),
  });
  return {
    __esModule: true,
    default: { connect: jest.fn(fakeClient) },
  };
});

beforeEach(async () => {
  await AsyncStorage.clear();
});

test('renders correctly', async () => {
  await ReactTestRenderer.act(() => {
    ReactTestRenderer.create(<App />);
  });
});