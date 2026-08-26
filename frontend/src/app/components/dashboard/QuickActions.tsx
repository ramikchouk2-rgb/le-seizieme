'use client';

import Link from 'next/link';

interface QuickActionsProps {
  actions: {
    label: string;
    icon: string;
    description?: string;
    href?: string;
    onClick?: () => void;
    variant?: 'primary' | 'secondary';
    loading?: boolean;
    disabled?: boolean;
  }[];
}

export default function QuickActions({ actions }: QuickActionsProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions rapides</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {actions.map((action, index) => {
          const content = (
            <>
              <span className="text-2xl">{action.icon}</span>
              <span className="text-xs font-medium text-center">{action.label}</span>
              {action.description && (
                <span className="text-[10px] text-gray-500 text-center leading-tight">{action.description}</span>
              )}
            </>
          );
          const disabled = action.disabled || action.loading;
          const className = `flex flex-col items-center justify-center gap-1 p-4 rounded-lg border transition-colors ${
            action.variant === 'primary'
              ? 'bg-[#D4AF37] text-white border-[#D4AF37] hover:bg-[#B8941E]'
              : 'bg-white text-gray-700 border-gray-200 hover:border-[#D4AF37] hover:text-[#D4AF37]'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`;

          if (action.href) {
            return (
              <Link
                key={index}
                href={disabled ? '#' : action.href}
                className={className}
                onClick={(e) => disabled && e.preventDefault()}
              >
                {content}
              </Link>
            );
          }
          return (
            <button
              key={index}
              onClick={action.onClick}
              disabled={disabled}
              className={className}
            >
              {content}
            </button>
          );
        })}
      </div>
    </div>
  );
}
