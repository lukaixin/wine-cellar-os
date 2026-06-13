from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any


class DrinkWindowStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    TOO_EARLY = "TOO_EARLY"
    ENTERING = "ENTERING"
    IN_WINDOW = "IN_WINDOW"
    LATE = "LATE"
    PAST = "PAST"


@dataclass(frozen=True)
class DrinkWindowClassification:
    status: DrinkWindowStatus
    drink_from: int | None
    drink_to: int | None
    confidence: str | None
    years_until_start: int | None
    years_past_end: int | None
    message: str

    def to_read_dict(self) -> dict[str, str | int | None]:
        return {
            "drink_window_status": self.status.value,
            "drink_window_message": self.message,
            "years_until_drink_window": self.years_until_start,
            "years_past_drink_window": self.years_past_end,
        }


def classify_drink_window(
    drink_from: int | None,
    drink_to: int | None,
    confidence: str | None,
    today: date | None = None,
) -> DrinkWindowClassification:
    current_year = (today or date.today()).year
    if drink_from is None or drink_to is None:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.UNKNOWN,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=None,
            years_past_end=None,
            message="未设置完整适饮期。",
        )
    if drink_from > drink_to:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.UNKNOWN,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=None,
            years_past_end=None,
            message="适饮期起止年份不一致。",
        )
    if current_year < drink_from - 1:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.TOO_EARLY,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=drink_from - current_year,
            years_past_end=None,
            message=f"距离适饮期开始还有 {drink_from - current_year} 年。",
        )
    if current_year < drink_from:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.ENTERING,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=drink_from - current_year,
            years_past_end=None,
            message="即将进入适饮期。",
        )
    if current_year <= drink_to:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.IN_WINDOW,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=0,
            years_past_end=None,
            message="当前处于适饮期。",
        )
    if current_year == drink_to + 1:
        return DrinkWindowClassification(
            status=DrinkWindowStatus.LATE,
            drink_from=drink_from,
            drink_to=drink_to,
            confidence=confidence,
            years_until_start=None,
            years_past_end=1,
            message="刚过建议适饮期，需要优先检查。",
        )
    return DrinkWindowClassification(
        status=DrinkWindowStatus.PAST,
        drink_from=drink_from,
        drink_to=drink_to,
        confidence=confidence,
        years_until_start=None,
        years_past_end=current_year - drink_to,
        message=f"已超过建议适饮期 {current_year - drink_to} 年。",
    )


def classify_vintage(vintage: Any, today: date | None = None) -> DrinkWindowClassification:
    if vintage is None:
        return classify_drink_window(None, None, None, today=today)
    return classify_drink_window(
        vintage.default_drink_from,
        vintage.default_drink_to,
        vintage.drink_window_confidence,
        today=today,
    )
