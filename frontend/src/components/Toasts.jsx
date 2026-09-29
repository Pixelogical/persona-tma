import React from 'react'

const STYLES = {
  success: 'alert-success text-success-content',
  error: 'alert-error text-error-content',
  info: 'alert-info text-info-content',
  warning: 'alert-warning text-warning-content',
}

const ICONS = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' }

export default function Toasts({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="toast toast-top toast-center z-[100] w-[92%] max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`alert ${STYLES[t.type] || STYLES.info} shadow-card text-sm font-semibold fade-up py-2`}
        >
          <span className="text-base leading-none">{ICONS[t.type] || ICONS.info}</span>
          <span className="truncate">{t.msg}</span>
        </div>
      ))}
    </div>
  )
}
