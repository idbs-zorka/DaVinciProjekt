from rapidfuzz import process,fuzz
from typing import Any
def fuzzy_search(
        query: str,
        choice: list[str],
        limit: int | None = None,
        scorer: Any | None = fuzz.WRatio,
        score_cutoff: int | None = None
) -> list[str]:

    results = process.extract(
        query,
        choice,
        limit=limit,
        scorer=scorer,
        score_cutoff=score_cutoff
    )
    results.sort(key=lambda x: x[1],reverse=True)

    return [match for match, score, _ in results]