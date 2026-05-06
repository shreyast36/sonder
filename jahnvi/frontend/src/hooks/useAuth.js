// TODO: Jahnvi — Firebase Auth hook.
//
// useAuth() → { user, loading, signIn, signOut, signInWithGoogle }
//
// Wrap with onAuthStateChanged listener so the app reacts to login/logout.
//
// IMPORTANT — profile creation on first login:
//   After any successful sign-in, check if the user's profile exists in Firestore.
//   If it does not, call POST /api/users/profile to create it before continuing.
//   Every other API call assumes the profile exists — skipping this step will cause
//   silent 404s throughout the app.
//
//   Pattern:
//     onAuthStateChanged(auth, async (firebaseUser) => {
//       if (firebaseUser) {
//         const token = await firebaseUser.getIdToken()
//         const profile = await fetch("/api/users/profile", {
//           headers: { Authorization: `Bearer ${token}` }
//         })
//         if (profile.status === 404) {
//           // First login — create the profile
//           await fetch("/api/users/profile", {
//             method:  "POST",
//             headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
//             body:    JSON.stringify({ display_name: firebaseUser.displayName || "Traveller" }),
//           })
//         }
//         setUser(firebaseUser)
//       } else {
//         setUser(null)
//       }
//       setLoading(false)
//     })
//
// Token refresh:
//   Firebase ID tokens expire after 1 hour. Use getIdToken(true) to force-refresh,
//   or attach an Axios/fetch interceptor that retries on 401 with a fresh token.
//
// Exposed values:
//   user          — Firebase User object (null if not logged in)
//   loading       — true until onAuthStateChanged fires for the first time
//   signIn()      — email/password sign-in
//   signOut()     — sign out and clear local state
//   signInWithGoogle() — Google OAuth popup
