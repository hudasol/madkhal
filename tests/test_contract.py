from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from madkhal import contract as c
from madkhal.contract import export
from madkhal.core import paths

from . import factories


@pytest.mark.req("MK-L0-001")
def test_every_contract_model_has_a_factory_instance() -> None:
    names = {type(o).__name__ for o in factories.all_instances()}
    assert names == set(export.model_names())


@pytest.mark.req("MK-L0-001")
@pytest.mark.parametrize("obj", factories.all_instances(), ids=lambda o: type(o).__name__)
def test_round_trip_json(obj: Any) -> None:
    again = type(obj).model_validate_json(obj.model_dump_json())
    assert again == obj


@pytest.mark.req("MK-L0-002")
def test_generated_artefacts_are_fresh() -> None:
    root = paths.repo_root()
    for rel, text in export.artefacts().items():
        path = root / rel
        assert path.is_file(), f"{rel} missing; run madkhal docs build"
        assert path.read_text(encoding="utf-8") == text, f"{rel} is stale; run madkhal docs build"


@pytest.mark.req("MK-L0-002")
def test_typescript_has_every_model_and_enum() -> None:
    ts = export.typescript()
    for name in export.model_names():
        assert f"export interface {name} " in ts
    for enum in export.ENUMS:
        assert f"export type {enum.__name__} = " in ts


@pytest.mark.req("MK-L0-003")
def test_parameter_without_evidence_level_is_rejected() -> None:
    data = factories.parameter().model_dump()
    del data["evidence_level"]
    with pytest.raises(ValidationError, match="evidence_level"):
        c.Parameter(**data)


@pytest.mark.req("MK-L0-003")
def test_assumption_spread_must_be_at_least_25_percent() -> None:
    with pytest.raises(ValidationError, match="spread"):
        factories.parameter(rel_spread=0.1)
    factories.parameter(source="literature", evidence_level="L1", rel_spread=0.1)


@pytest.mark.req("MK-L0-003")
def test_assumption_cannot_claim_a_higher_evidence_level() -> None:
    with pytest.raises(ValidationError, match="L0"):
        factories.parameter(evidence_level="L2")


@pytest.mark.req("MK-L0-004")
def test_advisory_without_explanation_is_rejected() -> None:
    data = factories.advisory().model_dump()
    del data["explanation"]
    with pytest.raises(ValidationError, match="explanation"):
        c.Advisory(**data)


@pytest.mark.req("MK-L0-005")
def test_probabilities_are_bounded() -> None:
    with pytest.raises(ValidationError):
        factories.advisory(p_breach_full_scale=1.2)
    with pytest.raises(ValidationError):
        c.ConstraintStatus(name="fouling", value=0.1, budget=0.05, used_percent=150.0)


@pytest.mark.req("MK-L0-005")
def test_timestamps_are_stored_in_utc_and_naive_times_rejected() -> None:
    dubai = dt.timezone(dt.timedelta(hours=4))
    a = factories.advisory(issued_for=dt.datetime(2020, 1, 1, 10, tzinfo=dubai))
    assert a.issued_for.utcoffset() == dt.timedelta(0)
    assert a.issued_for.hour == 6
    with pytest.raises(ValidationError):
        factories.advisory(issued_for=dt.datetime(2020, 1, 1, 10))


@pytest.mark.req("MK-L0-005")
def test_units_declared_in_the_dictionary() -> None:
    fd = export.field_dictionary()
    assert fd["Limits"]["fields"]["water_allowance_m3"]["unit"] == "m3"
    assert fd["PlantState"]["fields"]["storage_hours"]["unit"] == "h"
    assert fd["Advisory"]["fields"]["p_breach_full_scale"]["unit"] == "1"


@pytest.mark.req("MK-L0-005")
def test_rate_must_match_counts() -> None:
    with pytest.raises(ValidationError):
        c.RateWithCounts(k=1, n=3, rate=0.5)
    with pytest.raises(ValidationError):
        c.RateWithCounts(k=4, n=3, rate=4 / 3)


@pytest.mark.req("MK-L0-006")
def test_every_field_has_english_and_arabic_descriptions() -> None:
    missing = []
    for model, entry in export.field_dictionary().items():
        for fname, f in entry["fields"].items():
            if not f["en"].strip() or not f["ar"].strip():
                missing.append(f"{model}.{fname}")
            elif not any("؀" <= ch <= "ۿ" for ch in f["ar"]):
                missing.append(f"{model}.{fname} (no Arabic script)")
    assert missing == []


@pytest.mark.req("MK-L0-001")
def test_restrictiveness_order() -> None:
    order = [
        c.restrictiveness(c.ActionKind.GO, 1.0),
        c.restrictiveness(c.ActionKind.DERATE, 0.9),
        c.restrictiveness(c.ActionKind.DERATE, 0.2),
        c.restrictiveness(c.ActionKind.PARK, 0.0),
        c.restrictiveness(c.ActionKind.NO_SAFE_OPTION_ESCALATE, 0.0),
    ]
    assert order == sorted(order)
    assert len(set(order)) == len(order)


@pytest.mark.req("MK-L0-001")
def test_mission_notice_is_the_simulation_statement() -> None:
    m = factories.all_instances()[-1]
    assert m.notice == c.SIMULATION_NOTICE
    with pytest.raises(ValidationError):
        type(m)(**{**m.model_dump(), "notice": "flight approved"})
