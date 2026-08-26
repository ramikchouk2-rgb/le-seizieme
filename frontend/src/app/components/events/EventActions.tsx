'use client';

interface EventActionsProps {
  onGenerateTeam: () => void;
  onRecommendTransport: () => void;
  onLaunchUrgentOffers: () => void;
  onViewStaffing: () => void;
}

export default function EventActions({
  onGenerateTeam,
  onRecommendTransport,
  onLaunchUrgentOffers,
  onViewStaffing,
}: EventActionsProps) {
  const actions = [
    { label: 'Générer l\'équipe', icon: '👥', onClick: onGenerateTeam, primary: true },
    { label: 'Recommander le transport', icon: '🚗', onClick: onRecommendTransport, primary: false },
    { label: 'Lancer les offres urgentes', icon: '⚡', onClick: onLaunchUrgentOffers, primary: false },
    { label: 'Voir le staffing', icon: '📋', onClick: onViewStaffing, primary: false },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {actions.map((action) => (
        <button
          key={action.label}
          onClick={action.onClick}
          disabled
          className={`px-3 py-2 text-sm font-medium rounded-lg border ${
            action.primary
              ? 'bg-[#D4AF37] text-white border-[#D4AF37]'
              : 'bg-white text-gray-700 border-gray-200'
          } opacity-50 cursor-not-allowed`}
          title="Bientôt disponible"
        >
          <span className="mr-1">{action.icon}</span>
          {action.label}
        </button>
      ))}
      <p className="col-span-2 text-xs text-gray-400 mt-1 italic">Ces actions seront disponibles prochainement.</p>
    </div>
  );
}
