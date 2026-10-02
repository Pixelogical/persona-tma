import React from 'react'
import ProfileSheet from './ProfileSheet'

export default function ProfileModal({ userId, onClose }) {
  if (!userId) return null
  return (
    <div className="modal modal-open animate-fadein">
      <div className="modal-box glass max-w-md border border-base-content/10 max-h-[90vh]">
        <button
          className="btn btn-sm btn-circle btn-ghost absolute right-3 top-3 z-10"
          onClick={onClose}
          aria-label="Close"
        >
          ✕
        </button>
        <ProfileSheet key={userId} userId={userId} />
      </div>
      <div className="modal-backdrop pointer-events-none" />
    </div>
  )
}
