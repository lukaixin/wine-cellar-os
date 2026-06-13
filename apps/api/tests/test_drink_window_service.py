from datetime import date

import pytest

from app.services.drink_window_service import DrinkWindowStatus, classify_drink_window


@pytest.mark.parametrize(
    ("drink_from", "drink_to", "expected"),
    [
        (None, None, DrinkWindowStatus.UNKNOWN),
        (2030, 2035, DrinkWindowStatus.TOO_EARLY),
        (2027, 2032, DrinkWindowStatus.ENTERING),
        (2024, 2028, DrinkWindowStatus.IN_WINDOW),
        (2020, 2025, DrinkWindowStatus.LATE),
        (2018, 2023, DrinkWindowStatus.PAST),
    ],
)
def test_drink_window_classification_statuses(
    drink_from: int | None,
    drink_to: int | None,
    expected: DrinkWindowStatus,
) -> None:
    classification = classify_drink_window(drink_from, drink_to, "low", today=date(2026, 6, 13))

    assert classification.status == expected


def test_drink_window_classification_tracks_year_offsets() -> None:
    too_early = classify_drink_window(2030, 2035, "medium", today=date(2026, 6, 13))
    past = classify_drink_window(2018, 2023, "medium", today=date(2026, 6, 13))

    assert too_early.years_until_start == 4
    assert too_early.years_past_end is None
    assert past.years_until_start is None
    assert past.years_past_end == 3
