from enum import Enum


class ValidationStatus(str, Enum):
    approved = "approved"
    revise   = "revise"


class VisaRequirement(str, Enum):
    visa_free       = "visa_free"
    visa_on_arrival = "visa_on_arrival"
    visa_required   = "visa_required"
    unknown         = "unknown"
