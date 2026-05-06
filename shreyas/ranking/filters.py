# TODO: Shreyas — hard constraint filtering before scoring.
# - apply_destination_filters(destinations, constraints) → list[Destination]
#   Remove destinations that exceed daily budget * 1.3 or match avoid_list tags.
# - apply_activity_filters(activities, constraints) → list[Activity]
#   Remove activities whose tags overlap with avoid_list.
