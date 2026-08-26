export const FEATURES = {
  ENABLE_GAMIFICATION: true,
  ENABLE_URGENT_STAFFING: true,
  ENABLE_TRANSPORT: true,
  ENABLE_ANALYTICS: false,
  ENABLE_DARK_MODE: false,
} as const;

export type FeatureFlag = keyof typeof FEATURES;

export function isFeatureEnabled(flag: FeatureFlag): boolean {
  return FEATURES[flag];
}

export function getFeatureFlags() {
  return { ...FEATURES };
}
