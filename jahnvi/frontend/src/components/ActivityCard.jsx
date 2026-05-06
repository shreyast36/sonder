// TODO: Jahnvi — reusable activity card component.
// Props: activity (Activity), time (string), whyThis (string), addedBy (string | null),
//        onFeedback ((ActivityFeedback) => void) | null
// Design ref: Figma screens 3 and 7.
//
// Per-activity feedback interactions (Screen 3):
//   - Tap "Why this?" chevron  → expand whyThis explanation inline
//   - Long-press card OR tap ⋮ → show bottom sheet: "Swap this" | "Remove" | "Adjust time"
//   - On selection: call onFeedback({ activity_id, action, reason }) which appends to
//     a local activity_feedback list; user confirms with a single "Update itinerary" button
//     that calls updateTrip({ feedback: "", activity_feedback: [...] })
//   - Do NOT fire a separate API call per tap — batch all activity feedback with the confirm
