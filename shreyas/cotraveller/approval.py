# TODO: Shreyas — approve/deny match logic.
# - approve_match(session_id, user_id) → ApprovalStatus
#   Mark user's approval in Firestore. If both users approved → trigger shared itinerary creation.
# - deny_match(session_id, user_id) → ApprovalStatus
#   Mark denial, close session, notify other user in real time.
# - get_approval_status(session_id) → ApprovalStatus
