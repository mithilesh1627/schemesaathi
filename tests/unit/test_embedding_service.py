"""Unit tests for local multilingual pretrained embedding service (BAAI/bge-m3)."""

from src.modules.retrieval.application.embedding_service import local_embedder


def test_embedding_dimension_and_normalization() -> None:
    """Verify output vector is strictly 1024 dimensions and unit normalized (L2 norm = 1.0)."""
    text = "Post-Matric Scholarship for ST Students in Manipur"
    vec = local_embedder.embed_text(text)

    assert len(vec) == 1024
    assert local_embedder.dimension == 1024
    assert local_embedder.model_name == "BAAI/bge-m3"
    assert local_embedder.model_version == "v1"

    norm_sq = sum(x * x for x in vec)
    assert abs(norm_sq - 1.0) < 1e-4


def test_embedding_reproducibility() -> None:
    """Verify identical text produces bit-exact identical embeddings."""
    t = "Chief Minister's College Students Rehabilitation Scheme CMCSRS"
    v1 = local_embedder.embed_text(t)
    v2 = local_embedder.embed_text(t)

    assert v1 == v2


def test_embedding_semantic_paraphrase_similarity() -> None:
    """Verify paraphrase-level semantic similarity beyond keyword overlap.

    Sentences A and B convey the exact same statutory eligibility rule
    using distinct vocabulary and syntax (no keyword overlap), while
    sentence C is an unrelated physics statement.
    """
    sentence_a = "Household earnings must remain below two and a half lakh rupees per year for tribal college learners."
    sentence_b = "Scheduled tribe undergraduate applicants qualify only when annual parental compensation does not exceed 250000 INR."
    sentence_unrelated = "Quantum chromodynamics describes strong nuclear interactions binding quarks and gluons inside hadrons."

    vec_a = local_embedder.embed_text(sentence_a)
    vec_b = local_embedder.embed_text(sentence_b)
    vec_c = local_embedder.embed_text(sentence_unrelated)

    def dot_product(u: list[float], v: list[float]) -> float:
        return sum(x * y for x, y in zip(u, v, strict=False))

    sim_paraphrase = dot_product(vec_a, vec_b)
    sim_unrelated = dot_product(vec_a, vec_c)

    # Paraphrase semantic similarity must comfortably exceed unrelated similarity
    assert sim_paraphrase > 0.60, f"Expected paraphrase similarity > 0.60, got {sim_paraphrase:.4f}"
    assert sim_unrelated < 0.35, f"Expected unrelated similarity < 0.35, got {sim_unrelated:.4f}"
    assert sim_paraphrase - sim_unrelated > 0.35, (
        f"Paraphrase margin too low: {sim_paraphrase:.4f} vs {sim_unrelated:.4f}"
    )


def test_batch_embedding_consistency() -> None:
    """Verify batch embedding produces identical vectors to single embed_text calls."""
    texts = [
        "Financial assistance for college students",
        "Displaced undergraduate rehabilitation framework",
        "",
    ]
    batch_vecs = local_embedder.embed_batch(texts)
    assert len(batch_vecs) == len(texts)
    assert len(batch_vecs[0]) == 1024
    expected = local_embedder.embed_text(texts[0])
    for actual_val, exp_val in zip(batch_vecs[0], expected, strict=True):
        assert abs(actual_val - exp_val) < 1e-4
