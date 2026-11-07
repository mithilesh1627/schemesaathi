"""Unit tests for DeterministicStateSynchronizer."""

from src.modules.chat.application.synchronizer import DeterministicStateSynchronizer
from src.modules.chat.domain.models import ChatSession, UserProfileFacts


def test_extract_profile_updates_from_natural_language() -> None:
    """Verify natural language extraction of profile facts."""
    # 1. Income extraction with rupee symbol and commas
    text1 = "actually my annual family income is ₹150,000"
    up1 = DeterministicStateSynchronizer.extract_profile_updates(text1)
    assert up1["annual_family_income_inr"] == 150000.0

    # 2. Income extraction with lakh
    text2 = "my income is 2.5 lakh"
    up2 = DeterministicStateSynchronizer.extract_profile_updates(text2)
    assert up2["annual_family_income_inr"] == 250000.0

    # 3. Marks extraction
    text3 = "my score is 72.5%"
    up3 = DeterministicStateSynchronizer.extract_profile_updates(text3)
    assert up3["marks_percent"] == 72.5

    # 4. Social category extraction
    text4 = "I am an ST applicant"
    up4 = DeterministicStateSynchronizer.extract_profile_updates(text4)
    assert up4["social_category"] == "ST"

    # 5. Conflict displacement extraction
    text5 = "I am displaced from my home district"
    up5 = DeterministicStateSynchronizer.extract_profile_updates(text5)
    assert up5["is_displaced"] is True

    text6 = "I am non-displaced"
    up6 = DeterministicStateSynchronizer.extract_profile_updates(text6)
    assert up6["is_displaced"] is False

    # 6. Course level extraction
    text7 = "Currently studying in UG course"
    up7 = DeterministicStateSynchronizer.extract_profile_updates(text7)
    assert up7["course_level"] == "UNDERGRADUATE"


def test_apply_updates_to_session() -> None:
    """Verify updates apply to session profile facts and track changed fields."""
    session = ChatSession(
        session_id="test-session-sync",
        profile_facts=UserProfileFacts(
            domicile_state="MANIPUR",
            social_category="ST",
            annual_family_income_inr=200000.0,
            marks_percent=65.0,
            course_level="UNDERGRADUATE",
            is_displaced=False,
        ),
    )

    # User corrects income mid-conversation
    changed = DeterministicStateSynchronizer.apply_updates(
        session=session,
        message_text="actually my income is ₹120,000",
    )
    assert "annual_family_income_inr" in changed
    assert session.profile_facts.annual_family_income_inr == 120000.0


def test_serialize_synchronizer_state_marks_missing_fields() -> None:
    """Verify synchronizer explicitly marks missing fields as [MISSING] in prompt."""
    partial_facts = UserProfileFacts(
        domicile_state="MANIPUR",
        social_category="ST",
        annual_family_income_inr=None,  # Missing!
        marks_percent=None,  # Missing!
        course_level="UNDERGRADUATE",
        is_displaced=None,  # Missing!
    )

    state_str = DeterministicStateSynchronizer.serialize_synchronizer_state(partial_facts)

    assert "Domicile State: MANIPUR" in state_str
    assert "Social Category: ST" in state_str
    assert "Annual Family Income: [MISSING]" in state_str
    assert "Qualifying Marks Percent: [MISSING]" in state_str
    assert "Conflict Displaced Status: [MISSING]" in state_str
    assert (
        "Unsupplied Required Fields: annual_family_income_inr, marks_percent, is_displaced"
        in state_str
    )
