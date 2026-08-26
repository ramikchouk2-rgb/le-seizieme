'use client';

interface EventReportAlertsProps {
  alerts: {
    type: string;
    severity: string;
    message: string;
    related_entity?: string | null;
  }[];
}

export default function EventReportAlerts({ alerts }: EventReportAlertsProps) {
  const severityStyles: Record<string, string> = {
    CRITICAL: 'bg-red-50 text-red-700 border-red-200',
    WARNING: 'bg-orange-50 text-orange-700 border-orange-200',
    INFO: 'bg-blue-50 text-blue-700 border-blue-200',
  };

  const severityIcons: Record<string, string> = {
    CRITICAL: '🔴',
    WARNING: '🟠',
    INFO: '🔵',
  };

  if (alerts.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="p-4 md:p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Alertes et observations</h2>
      </div>
      <div className="p-4 md:p-6 space-y-3">
        {alerts.map((alert, index) => (
          <div
            key={index}
            className={`flex items-start gap-3 p-3 rounded-lg border ${severityStyles[alert.severity] || 'bg-gray-50 text-gray-700 border-gray-200'}`}
          >
            <span className="text-lg leading-none">{severityIcons[alert.severity] || '•'}</span>
            <div className="flex-1">
              <p className="text-sm font-medium">{alert.message}</p>
              {alert.related_entity && (
                <p className="text-xs opacity-75 mt-1">ID: {alert.related_entity}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
