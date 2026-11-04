"""Manual smoke test for the real BAAI/bge-m3 embedding model.

Not part of the pytest suite: requires downloading the model (~2 GB) and
a CUDA-capable GPU. Run manually after installing the 'embeddings' extra:

    uv sync --extra embeddings
    uv run python scripts/smoke_test_embedding.py
"""

from policy_consultant.embedding import LocalBgeM3EmbeddingModel


def main() -> None:
    model = LocalBgeM3EmbeddingModel(device="cuda")
    print(f"model_id: {model.model_id}")
    print(f"dimensions: {model.dimensions}")

    texts = [
        "¿Cuántos días de vacaciones tengo en España?",
        "How many vacation days do I have in Spain?",
        "La tabla de antigüedad de México tiene siete tramos.",
    ]
    embeddings = model.embed_batch(texts)

    for text, embedding in zip(texts, embeddings, strict=True):
        print(f"len={len(embedding)} first_values={embedding[:4]} text={text!r}")

    if not all(len(embedding) == model.dimensions for embedding in embeddings):
        raise AssertionError("An embedding did not match the reported dimensionality")

    print("OK: all embeddings match the reported dimensionality.")


if __name__ == "__main__":
    main()
