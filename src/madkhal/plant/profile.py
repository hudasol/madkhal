"""The default hypothetical plant profile. Every value is an illustrative assumption.

The plant is a stylised SWRO unit of illustrative size: offshore intake, pretreatment
(coagulation with dissolved air flotation), one RO train and a product water store. It
resembles no real asset. No value below was taken from a real plant or from a source; each
is an ASSUMPTION at evidence level L0 with a relative spread of at least 25 percent.
"""

from __future__ import annotations

from madkhal.contract import EvidenceLevel, Parameter, ParamSource, PlantProfile

ASSUMPTION_SPREAD = 0.3
# Quantities an operator knows at decision time; the decision uses them at their value.
OPERATING = {"plant.design_flow_m3h", "plant.demand_fraction", "plant.storage_capacity_h"}

_ROWS: list[tuple[str, str, float, str, str, str]] = [
    # key, label, value, unit, adverse direction, reasoning
    (
        "plant.design_flow_m3h",
        "Product flow at full scale",
        2000.0,
        "m3/h",
        "up",
        "Illustrative size only; scales every water volume",
    ),
    (
        "plant.demand_fraction",
        "Demand as a share of full scale flow",
        0.7,
        "1",
        "up",
        "Plants usually run below nameplate; illustrative",
    ),
    (
        "plant.storage_capacity_h",
        "Product storage capacity",
        36.0,
        "h",
        "down",
        "A day and a half of demand; illustrative",
    ),
    (
        "plant.background_load",
        "Intake organic load without a bloom",
        0.35,
        "1",
        "up",
        "Relative to a pretreatment design load of 1.0",
    ),
    (
        "plant.bloom_load_min",
        "Smallest bloom load added at the intake",
        0.5,
        "1",
        "up",
        "Lower bound of the Pareto bloom load; relative to design load",
    ),
    (
        "plant.bloom_tail_alpha",
        "Pareto tail index of the bloom load",
        2.5,
        "1",
        "down",
        "Heavy tailed: a smaller index means more extreme blooms",
    ),
    (
        "plant.pretreat_capacity",
        "Pretreatment capacity before breakthrough",
        1.1,
        "1",
        "down",
        "Ten percent margin over the design load",
    ),
    (
        "plant.coagulant_boost",
        "Extra pretreatment capacity from a coagulant boost",
        0.5,
        "1",
        "down",
        "Applied only when derating",
    ),
    (
        "plant.k_fouling",
        "Fouling index rise per unit breakthrough per hour",
        0.03,
        "1/h",
        "up",
        "Sets how fast breakthrough reaches the hard limit",
    ),
    (
        "plant.fouling_after_clean",
        "Fouling index after a cleaning",
        0.1,
        "1",
        "up",
        "Cleaning is not perfect",
    ),
    (
        "plant.clean_hours",
        "Downtime of a forced cleaning",
        24.0,
        "h",
        "up",
        "Clean in place plus flushing",
    ),
    (
        "plant.restart_hours",
        "Minimum restart time after a stop",
        6.0,
        "h",
        "up",
        "Restart penalty after PARK or a forced shutdown",
    ),
    (
        "plant.planned_clean_at",
        "Fouling index that triggers a planned cleaning",
        0.6,
        "1",
        "up",
        "Maintenance practice in the lab simulation",
    ),
    (
        "plant.planned_clean_hours",
        "Downtime of a planned cleaning",
        12.0,
        "h",
        "up",
        "Shorter than a forced cleaning",
    ),
    (
        "plant.wear_per_clean",
        "Membrane life used by one cleaning",
        1.0,
        "1",
        "up",
        "Index units; a forced cleaning counts double",
    ),
    (
        "plant.wear_per_breakthrough",
        "Membrane life used per unit breakthrough hour",
        0.05,
        "1",
        "up",
        "Index units",
    ),
]


def default_profile() -> PlantProfile:
    """The hypothetical plant used everywhere unless a caller supplies another profile."""
    return PlantProfile(
        id="hypothetical-swro-1",
        name="Hypothetical SWRO unit (illustrative size)",
        hypothetical=True,
        description=(
            "Stylised SWRO unit: offshore intake, coagulation with dissolved air flotation, "
            "one RO train and a product water store. Illustrative size; resembles no real "
            "asset. Every parameter is an assumption (evidence level L0)."
        ),
        parameters=[
            Parameter(
                key=k,
                label=lab,
                value=v,
                unit=u,
                evidence_level=EvidenceLevel.L0,
                source=ParamSource.assumption,
                provenance=f"ASSUMPTION: {why}",
                rel_spread=ASSUMPTION_SPREAD,
                adverse=adv,
                role="operating" if k in OPERATING else "physics",
            )
            for k, lab, v, u, adv, why in _ROWS
        ],
    )


PARAMETER_KEYS = tuple(r[0] for r in _ROWS)
