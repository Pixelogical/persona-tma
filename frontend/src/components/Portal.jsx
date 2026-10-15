import { createPortal } from 'react-dom'

/**
 * Renders its children straight into <body>. Every view is wrapped in the
 * fade-up animation whose transform turns it into the containing block of
 * position:fixed descendants — modals rendered inside views therefore got
 * clipped and painted under the sticky header / bottom nav. Portaling to
 * body escapes all of that.
 */
export default function Portal({ children }) {
  return createPortal(children, document.body)
}
