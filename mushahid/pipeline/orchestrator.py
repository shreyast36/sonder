# TODO: Mushahid — main pipeline orchestrator. Coordinates all 6 modules in sequence.
# run_plan_trip_pipeline(user_profile: UserProfile) → AsyncGenerator[SSEEvent, None]
#   Step 1: Jahnvi's module3_persona.py → emit "persona_inferring" / "persona_inferred"
#   Step 2: Shreyas's search.py → emit "retrieving" / "retrieval_done"
#   Step 3: Shreyas's ranking → emit "ranking" / "ranked"
#   Step 4: Ali's itinerary_generator.py → emit "generating" / "itinerary_generated"
#   Step 5: Ali's explainer.py → emit "explaining"
#   Step 6: Mushahid's validation → emit "validating" → if REVISE trigger refinement loop
#   Step 7: Shreyas's matching.py → emit "matching_cotravellers" / "matched"
#   Final: emit "done" with PlanTripResponse payload
