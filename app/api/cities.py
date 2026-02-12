from fastapi import APIRouter, Query

from app.data.cities import RUSSIAN_CITIES

router = APIRouter(prefix="/cities", tags=["Cities"])


@router.get("", response_model=list[str])
async def get_cities(
    search: str | None = Query(None, min_length=1, max_length=100, description="Search filter"),
) -> list[str]:
    """Return list of Russian cities, optionally filtered by search query."""
    if not search:
        return RUSSIAN_CITIES

    query = search.lower()
    return [city for city in RUSSIAN_CITIES if query in city.lower()]
