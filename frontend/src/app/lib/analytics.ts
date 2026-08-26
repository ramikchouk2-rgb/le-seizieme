type EventName =
  | 'event_created'
  | 'event_updated'
  | 'event_status_changed'
  | 'staff_recommendation_generated'
  | 'staff_assignments_confirmed'
  | 'staff_assignment_added'
  | 'staff_assignment_removed'
  | 'transport_recommended'
  | 'transport_confirmed'
  | 'urgent_offers_generated'
  | 'urgent_offer_accepted'
  | 'urgent_offer_declined'
  | 'attendance_initialized'
  | 'attendance_checked_in'
  | 'attendance_checked_out'
  | 'evaluation_created'
  | 'evaluation_updated'
  | 'evaluation_deleted'
  | 'completion_points_awarded'
  | 'performance_points_awarded'
  | 'rankings_calculated'
  | 'report_viewed'
  | 'server_viewed'
  | 'login'
  | 'logout';

interface EventParams {
  [key: string]: string | number | boolean | undefined;
}

let analyticsEnabled = false;
let analyticsEndpoint = '/api/analytics/events';

export function initAnalytics(options: { enabled?: boolean; endpoint?: string } = {}) {
  analyticsEnabled = options.enabled ?? false;
  if (options.endpoint) {
    analyticsEndpoint = options.endpoint;
  }
}

export function trackEvent(name: EventName, params?: EventParams) {
  if (!analyticsEnabled) return;

  const payload = {
    name,
    params: Object.fromEntries(
      Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null)
    ),
    timestamp: new Date().toISOString(),
    url: typeof window !== 'undefined' ? window.location.pathname : undefined,
  };

  if (typeof window !== 'undefined' && navigator.sendBeacon) {
    navigator.sendBeacon(analyticsEndpoint, JSON.stringify(payload));
  } else {
    fetch(analyticsEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      // analytics should never break the app
    });
  }
}

export function setAnalyticsEnabled(enabled: boolean) {
  analyticsEnabled = enabled;
}
