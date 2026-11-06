"""Unit tests for local reproducible deterministic embedding generator."""

from src.modules.retrieval.application.embedding_service import local_embedder


def test_embedding_dimension_and_normalization() -> None:
    """Verify output vector is strictly 1536 dimensions and unit normalized (L2 norm = 1.0)."""
    text = "Post-Matric Scholarship for ST Students in Manipur"
    vec = local_embedder.embed_text(text)

    assert len(vec) == 1536
    assert local_embedder.dimension == 1536
    assert local_embedder.model_name == "schemesaathi-deterministic-v1"
    assert local_embedder.model_version == "v1"

    norm_sq = sum(x * x for x in vec)
    assert abs(norm_sq - 1.0) < 1e-5


def test_embedding_reproducibility() -> None:
    """Verify identical text produces bit-exact identical embeddings."""
    t = "Chief Minister's College Students Rehabilitation Scheme CMCSRS"
    v1 = local_embedder.embed_text(t)
    v2 = local_embedder.embed_text(t)

    assert v1 == v2


def test_embedding_semantic_distance() -> None:
    """Verify semantically related texts have higher cosine similarity than unrelated texts."""
    v_st1 = local_embedder.embed_text(
        "Post-Matric Scholarship for ST Students Manipur income ceiling"
    )
    v_st2 = local_embedder.embed_text("ST scholarship post-matric income limit")
    v_astronomy = local_embedder.embed_text(
        "interstellar supernova pulsar black hole event horizon"
    )

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=False))

    sim_related = dot(v_st1, v_st2)
    sim_unrelated = dot(v_st1, v_astronomy)

    assert sim_related > 0.6
    assert sim_unrelated < 0.2
