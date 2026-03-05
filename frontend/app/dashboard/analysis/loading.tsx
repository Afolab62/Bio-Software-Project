// Next.js Loading Component
// This file is a special Next.js convention for showing loading states
// Location: app/dashboard/loading.tsx (or similar)
//
// HOW IT WORKS:
// - Next.js automatically shows this component while a page is loading
// - This happens during server-side rendering or when navigating between pages
// - Once the actual page loads, Next.js replaces this with the real content

// This is useful for:
// - Preventing flash of unstyled content
// - Showing smooth transitions between pages
// - Keeping UI clean during navigation

export default function Loading() {
  return null; // Shows nothing while page loads (you can customize this)
}
