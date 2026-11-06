"""Unit tests for Unicode script detection and trie-based transliteration router."""

from src.modules.retrieval.domain.models import QueryScript
from src.modules.retrieval.domain.script_router import ScriptRouter, TransliterationTrie


def test_unicode_script_detection() -> None:
    """Verify script classifier on Meetei Mayek, Bengali script, and Romanized Latin."""
    router = ScriptRouter()

    # Meetei Mayek
    assert router.detect_script("ꯃꯅꯤꯄꯨꯔ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ") == QueryScript.MEETEI_MAYEK
    assert router.detect_script("ꯑꯦꯁ.ꯇꯤ. ꯃꯦꯠꯔꯤꯛ") == QueryScript.MEETEI_MAYEK

    # Bengali script
    assert router.detect_script("মণিপুর স্কোলারশিপ") == QueryScript.BENGALI
    assert router.detect_script("মেট্রিক মতুং স্কলারশিপ") == QueryScript.BENGALI

    # Latin / English
    assert router.detect_script("Manipur ST scholarship") == QueryScript.LATIN
    assert router.detect_script("skolarsip matung senthok") == QueryScript.LATIN


def test_trie_prefix_matching() -> None:
    """Verify prefix trie longest matching logic."""
    trie = TransliterationTrie()
    trie.insert("matric", "matric")
    trie.insert("matric matung", "post-matric")

    match_len, translation = trie.match_longest(["matric", "matung", "scholarship"], 0)
    assert match_len == 2
    assert translation == "post-matric"

    match_len, translation = trie.match_longest(["matric", "alone"], 0)
    assert match_len == 1
    assert translation == "matric"


def test_script_router_meetei_mayek_transliteration() -> None:
    """Verify Meetei Mayek concepts are mapped to canonical English for retrieval."""
    router = ScriptRouter()
    res = router.route_query("ꯃꯅꯤꯄꯨꯔ ꯑꯦꯁ.ꯇꯤ. ꯃꯦꯠꯔꯤꯛ ꯃꯇꯨꯡ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ")

    assert res.detected_script == QueryScript.MEETEI_MAYEK
    assert res.is_transliterated is True
    assert "Manipur" in res.translated_concept_query
    assert "ST" in res.translated_concept_query
    assert "post-matric" in res.translated_concept_query
    assert "scholarship" in res.translated_concept_query


def test_script_router_bengali_transliteration() -> None:
    """Verify Bengali script concepts are mapped to canonical English."""
    router = ScriptRouter()
    res = router.route_query("মণিপুর এস.টি মেট্রিক মতুং স্কোলারশিপ")

    assert res.detected_script == QueryScript.BENGALI
    assert res.is_transliterated is True
    assert "Manipur" in res.translated_concept_query
    assert "ST" in res.translated_concept_query
    assert "post-matric" in res.translated_concept_query
    assert "scholarship" in res.translated_concept_query


def test_script_router_romanized_meiteilon() -> None:
    """Verify Romanized Meiteilon terms are mapped."""
    router = ScriptRouter()
    res = router.route_query("Manipur ST matung skolarsip")

    assert res.detected_script == QueryScript.LATIN
    assert res.is_transliterated is True
    assert "post-matric" in res.translated_concept_query
    assert "scholarship" in res.translated_concept_query


def test_unmapped_terms_fallback() -> None:
    """Verify unmapped terms are reported in metadata without being dropped."""
    router = ScriptRouter()
    res = router.route_query("ꯃꯅꯤꯄꯨꯔ unknowntermxyz")

    assert res.detected_script == QueryScript.MEETEI_MAYEK
    assert "unknowntermxyz" in res.unmapped_terms
    assert "unknowntermxyz" in res.translated_concept_query
