// TODO: Jahnvi — Screen 7: Shared Itinerary.
// Design ref: Figma screen 7 (same as Itinerary but "Added by Maya/You" labels, + Add Activity button).
// Subscribe to Firestore shared itinerary doc for live updates.
// Changes by either user sync in real time via Shreyas's shared_itinerary.py.
//
// Export actions (bottom sheet or share button in header):
//   "Send email"     → emailItinerary(itineraryId, [currentUserEmail, coTravellerEmail], includeNotes)
//                      POST /export/email — sends to both co-travellers
//   "Download PDF"   → window.open(apiBase + `/export/pdf/${itineraryId}?token=${idToken}`)
//                      GET /export/pdf/:itineraryId — streams PDF download
//
//   Show a loading state during email send; confirm with a toast on success.
//   PDF download opens in a new tab — browser handles the file save prompt.
