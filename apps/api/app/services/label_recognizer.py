from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.models import LabelImageUpload


@dataclass(frozen=True)
class LabelCandidateFields:
    producer_name: str | None = None
    wine_name: str | None = None
    vintage_year: int | None = None
    country: str | None = None
    region: str | None = None
    type: str | None = None
    bottle_size_ml: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class LabelRecognitionResult:
    recognizer: str
    confidence: str
    fields: LabelCandidateFields
    warnings: list[str] = field(default_factory=list)


class LabelRecognizer(Protocol):
    name: str

    def recognize(self, upload: LabelImageUpload) -> LabelRecognitionResult:
        ...


class MockLabelRecognizer:
    name = "mock-local-filename-heuristic"

    def recognize(self, upload: LabelImageUpload) -> LabelRecognitionResult:
        stem = Path(upload.original_filename).stem
        tokens = [token for token in re.split(r"[_\-\s]+", stem) if token]
        year = self._first_year(tokens)
        bottle_size_ml = self._first_size(tokens) or 750
        text_tokens = [token for token in tokens if not self._looks_structured(token)]

        producer_name = " ".join(text_tokens[:2]) if text_tokens else None
        wine_name = " ".join(text_tokens[2:]) if len(text_tokens) > 2 else None
        warnings = [
            "Mock recognizer uses filename heuristics only; verify all fields before confirming.",
        ]
        return LabelRecognitionResult(
            recognizer=self.name,
            confidence="low",
            fields=LabelCandidateFields(
                producer_name=producer_name,
                wine_name=wine_name,
                vintage_year=year,
                bottle_size_ml=bottle_size_ml,
                notes=f"Draft generated from local filename: {upload.original_filename}",
            ),
            warnings=warnings,
        )

    def _first_year(self, tokens: list[str]) -> int | None:
        for token in tokens:
            match = re.fullmatch(r"(19|20)\d{2}", token)
            if match:
                return int(match.group(0))
        return None

    def _first_size(self, tokens: list[str]) -> int | None:
        for token in tokens:
            match = re.fullmatch(r"(\d{3,4})ml", token.lower())
            if match:
                return int(match.group(1))
        return None

    def _looks_structured(self, token: str) -> bool:
        lower = token.lower()
        return bool(re.fullmatch(r"(19|20)\d{2}", lower) or re.fullmatch(r"\d{3,4}ml", lower))
