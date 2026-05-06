# TODO: Shreyas — score and rank retrieved destinations.
# - score_destination(dest, user_profile, pinecone_score) → float
#   Weighted combination: vector similarity (60%), budget fit (20%), tag-interest bonus (20%).
# - rank_destinations(candidates: list[tuple[Destination, float]], user_profile, top_n) → list[Destination]
#   Apply filters first, then score, then return top_n sorted by score descending.
