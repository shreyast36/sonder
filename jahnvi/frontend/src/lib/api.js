// TODO: Jahnvi — typed API client for the FastAPI backend.
// All requests attach the Firebase Auth ID token in the Authorization header.
//
// Helper:
//   async function authHeaders() {
//     const token = await auth.currentUser.getIdToken()
//     return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
//   }
//
// Endpoints:
//
//   createUserProfile(displayName)
//     POST /api/users/profile
//     Call once on first login (see useAuth.js). Idempotent — safe to call again.
//
//   getUserProfile()
//     GET /api/users/profile
//     Returns UserProfile JSON or 404 if not yet created.
//
//   planTrip(userProfile)
//     POST /api/plan-trip  → SSE stream
//     Returns a fetch() ReadableStream (not EventSource — needed for Auth header support).
//     Use useSSE.js to parse the named events.
//
//   updateTrip(request)
//     POST /api/update-trip → UpdateTripResponse
//     request: { itinerary_id, feedback?, activity_feedback?, current_itinerary }
//     Send feedback (string), activity_feedback (ActivityFeedback[]), or both.
//     activity_feedback: [{ activity_id, action: "swap"|"remove"|"adjust_time", reason? }]
//
//   getCotravellers(userId, itineraryId)
//     POST /api/cotraveller → list[CoTravellerMatch]
//
//   regenerateCotravellers(userId, excludedProfileIds, feedback)
//     POST /api/cotraveller/regenerate → list[CoTravellerMatch]
//     Call when user denies all current matches or taps "Show me different people".
//
//   startChat(userId, profileId, itineraryId)
//     POST /api/chat/start → ChatStartResponse { session, icebreaker, topics }
//     icebreaker: string — display as a pre-filled tap-to-send suggestion at top of chat
//     topics: string[5] — show as tappable chips at the bottom of Screen 5 (suggested topics bar)
//
//   approveMatch(sessionId, userId)
//     POST /api/chat/approve → { status: "approved" | "pending" }
//
//   denyMatch(sessionId, userId)
//     POST /api/chat/deny → { status: "denied" }
//
//   openChatSocket(sessionId, token)
//     Returns a WebSocket connected to /ws/chat/{sessionId}?token=<firebase_id_token>
//     Token passed as query param — browsers cannot set headers on WebSocket connections.
//
//     IMPORTANT — presence heartbeat:
//       After opening the socket, send {"type": "ping"} every ~30 seconds to keep the
//       user's presence alive. The backend TTL is 90s — missing 3 pings marks the user offline.
//       Clear the interval on socket close or component unmount.
//
//       Example:
//         const ws = openChatSocket(sessionId, token)
//         const pingInterval = setInterval(() => {
//           if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }))
//         }, 30_000)
//         ws.addEventListener("close", () => clearInterval(pingInterval))
