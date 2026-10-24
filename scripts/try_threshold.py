from app.services.embedding import embedding_service


def score(a: str, b: str) -> float:
    va = embedding_service.generate_embedding(a)
    vb = embedding_service.generate_embedding(b)
    return float(sum(x * y for x, y in zip(va, vb)))  # vectors are normalized, so this is cosine


pairs = [
    # should be treated as the SAME question (want: above 0.90)
    ("What is the capital of France?", "Which city is France's capital?"),
    ("How do I reset my password?", "I forgot my password, how can I change it?"),
    # DIFFERENT questions that look similar (want: below 0.90)
    ("What is the capital of France?", "What is the population of France?"),
    ("How do I reset my password?", "How do I reset my router?"),
    ("Translate 'hello' to French", "Translate 'hello' to Spanish"),
    # unrelated (want: far below)
    ("What is the capital of France?", "How do I bake bread?"),
    ("What is 2 + 2?", "What is 2 + 3?"),
    ("How do I enable dark mode?", "How do I disable dark mode?"),
    ("Who won the 2018 World Cup?", "Who won the 2022 World Cup?"),
    ("Name three uses of Redis.", "What are three things Redis is used for?"),
]

for a, b in pairs:
    s = score(a, b)
    verdict = "HIT " if s >= 0.85 else "miss"
    print(f"{s:.3f} {verdict}  {a!r}  vs  {b!r}")