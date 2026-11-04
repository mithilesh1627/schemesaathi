"""Domain Enums for Scheme Catalog and Eligibility."""

import enum


class SchemeLevel(enum.StrEnum):
    """Statutory issuing level of a scheme."""

    CENTRAL_SECTOR = "CENTRAL_SECTOR"
    CENTRALLY_SPONSORED = "CENTRALLY_SPONSORED"
    STATE_SECTOR = "STATE_SECTOR"
    CORPORATE_CSR_GOVT_PARTNERED = "CORPORATE_CSR_GOVT_PARTNERED"


class VerificationStatus(enum.StrEnum):
    """Verification status of a scheme or policy document version."""

    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
    OFFICIAL_PROVISIONAL = "OFFICIAL_PROVISIONAL"
    REQUIRES_REVALUATION = "REQUIRES_REVALUATION"
    DEPRECATED = "DEPRECATED"


class PortalType(enum.StrEnum):
    """Application portal identifier."""

    NSP_2_0 = "NSP_2_0"
    MYSCHEME = "MYSCHEME"
    STATE_DIRECT_PORTAL = "STATE_DIRECT_PORTAL"
    OFFLINE_INSTITUTE = "OFFLINE_INSTITUTE"


class PortalWindowStatus(enum.StrEnum):
    """Application portal operational window status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UPCOMING = "UPCOMING"
    EXTENDED = "EXTENDED"
    UNKNOWN = "UNKNOWN"


class EvaluationStatus(enum.StrEnum):
    """Outcome of a deterministic eligibility evaluation."""

    ELIGIBLE_NOW = "ELIGIBLE_NOW"
    ELIGIBLE_OFF_CYCLE = "ELIGIBLE_OFF_CYCLE"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
