// TODO: Jahnvi — Server-Sent Events hook for itinerary generation stream.
//
// useSSE(url, handlers) → { status, abort }
//
// `handlers` is an object keyed by SSE event name. Wire up every named event
// the backend emits so the UI updates stage by stage:
//
//   useSSE("/api/plan-trip", {
//     persona_inferring:      () => setStage("Understanding your travel style..."),
//     persona_inferred:       (data) => setPersona(data.archetype),
//     retrieving:             () => setStage("Finding the best destinations..."),
//     retrieval_done:         (data) => setDestinationCount(data.destination_count),
//     ranking:                () => setStage("Ranking options for you..."),
//     ranked:                 (data) => setTopDestination(data.top_destination),
//     generating:             (data) => appendTokenChunk(data.chunk),  // ← token-by-token, may fire many times
//     day_ready:              (data) => markDayReady(data.day_number, data.theme),
//     itinerary_generated:    () => setStage("Adding personalised insights..."),
//     explaining:             () => setStage("Explaining your activities..."),
//     validating:             () => setStage("Checking everything looks right..."),
//     revision:               (data) => setStage(`Refining... (attempt ${data.attempt})`),
//     validated:              (data) => setValidationScore(data.score),
//     matching_cotravellers:  () => setStage("Finding your perfect travel buddy..."),
//     matched:                (data) => setMatchCount(data.match_count),
//     done:                   (data) => setItinerary(data),  // full PlanTripResponse
//     error:                  (data) => showError(data.step, data.message),  // ← always handle this
//   })
//
// Notes:
//   - `generating` fires once per token chunk — buffer and append, do not replace
//   - `error` fires if the pipeline throws at any step; show a retry CTA, do not hang
//   - call abort() to close the EventSource early (e.g. user navigates away)
//   - attach the Firebase Auth token: new EventSource(url) doesn't support headers,
//     so pass the token as a query param: `/api/plan-trip?token=<id_token>`
//     OR use fetch() with ReadableStream to get header support (recommended)
