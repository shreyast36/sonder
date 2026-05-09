from enum import Enum


class ApprovalStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    denied   = "denied"
