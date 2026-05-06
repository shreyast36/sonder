# TODO: Shreyas — score and rank retrieved activities for a destination.
# - score_activity(activity, user_profile, pinecone_score) → float
#   Factor in category interest, cost vs. daily budget, pace preference.
# - rank_activities(candidates, user_profile, top_n) → list[Activity]
#   Apply filters, score, return top_n. Must respect pace: relaxed = fewer activities/day.
