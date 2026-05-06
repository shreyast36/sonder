// TODO: Jahnvi — Firestore real-time hooks.
//
// useDocument(collection, id) → { data, loading, error }
//   Subscribes to a single document with onSnapshot.
//   Unsubscribes on unmount.
//
// useCollection(collection, query) → { data, loading, error }
//   Subscribes to a collection query with onSnapshot.
//   Unsubscribes on unmount.
//
// useSharedItinerary(itineraryId) → { itinerary, version, loading, addActivity, addNote }
//   Specialised hook for Screen 7. Wraps the shared itinerary document and exposes
//   write helpers that handle HTTP 409 conflict responses.
//
//   Conflict handling (version mismatch):
//     When addActivity() or addNote() receives a 409 from the backend, it means
//     another user wrote to the itinerary between the last fetch and this write.
//     The hook should:
//       1. Re-fetch the latest SharedItinerary (sync_changes endpoint or onSnapshot)
//       2. Show a non-blocking toast: "Your co-traveller just made a change — review and try again"
//       3. Re-render with the latest version so the user can retry their edit
//     Do NOT silently retry — the user should see the latest state before writing.
//
//   Expected addActivity signature:
//     addActivity(activity, dayNumber) — reads current `version` from local state,
//     sends it to POST /api/shared-itinerary/{id}/activity, handles 409 as above.
