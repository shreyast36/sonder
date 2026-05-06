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
//
//   getCotravellers(userId, itineraryId)
//     POST /api/cotraveller → list[CoTravellerMatch]
//
//   regenerateCotravellers(userId, excludedProfileIds, feedback)
//     POST /api/cotraveller/regenerate → list[CoTravellerMatch]
//     Call when user denies all current matches or taps "Show me different people".
//
//   startChat(userId, profileId)
//     POST /api/chat/start → ChatSession
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
