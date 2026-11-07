"""Domain Enums for Grounded Chat, State Synchronization, and Readiness Audit."""

from enum import StrEnum


class ChatRole(StrEnum):
    """Message participant role in a conversation session."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AuditStatus(StrEnum):
    """Document readiness status evaluated against official statutory guidelines."""

    HAVE = "HAVE"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class LanguageScript(StrEnum):
    """Script and language classification detected by the Script Router."""

    ENGLISH = "English"
    MNI_LATN = "Romanized Meiteilon"
    MNI_BENG = "Bengali Script (Manipuri)"
    MNI_MTEI = "Meetei Mayek"
    UNKNOWN = "Unknown"
