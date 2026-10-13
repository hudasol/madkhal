"""Render docs/EVALUATION.md from results/*.json and mark every preregistered prediction.

Pure: takes the loaded results and returns text. Every number in the document is read from a
results file here; nothing is typed by hand.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .policies import POLICIES, POLICY_NAMES

R = dict[str, Any]


def fmt(x: float | int | None, digits: int = 3) -> str:
    if x is None:
        return "none"
    if isinstance(x, bool):
        return str(x)
    v = float(x)
    if v == 0:
        return "0"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.{digits}g}"


def paired(a: list[float], b: list[float]) -> dict[str, float]:
    """Mean of a minus b per seed with a 95 percent normal interval."""
    d = [x - y for x, y in zip(a, b, strict=True)]
    n = len(d)
    mean = sum(d) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1)) if n > 1 else 0.0
    half = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": mean, "lo": mean - half, "hi": mean + half, "n": n}


def ci(s: R, digits: int = 3) -> str:
    return f"{fmt(s['mean'], digits)} ({fmt(s['lo'], digits)} to {fmt(s['hi'], digits)})"


def _point(e7: R, site: str, event: str, anchor: str, days: int) -> R | None:
    for p in e7["sites"][site]["points"]:
        if p["event_id"] == event and p["anchor"] == anchor and p["days_before"] == days:
            return dict(p)
    return None


def predictions(res: dict[str, R]) -> list[dict[str, Any]]:
    """Each preregistered prediction with the observed value and HIT or MISS."""
    out: list[dict[str, Any]] = []

    def add(pid: str, text: str, observed: str, hit: bool | None) -> None:
        out.append(
            {
                "id": pid,
                "prediction": text,
                "observed": observed,
                "result": "HIT" if hit else ("MISS" if hit is not None else "NOT RUN"),
            }
        )

    e1 = res.get("e1")
    if e1:
        b = e1["brier"]
        m, a, p = b["madkhal"]["mean"], b["alert_means_bloom"]["mean"], b["persistence"]["mean"]
        add(
            "PR-E1-1",
            "Filter Brier lower than both baselines and at most 0.6 times persistence",
            f"filter {fmt(m)}, alert_means_bloom {fmt(a)}, persistence {fmt(p)} (ratio {fmt(m / p if p else None)})",
            m < a and m < p and m <= 0.6 * p,
        )
        ls = e1["log_score"]
        add(
            "PR-E1-2",
            "Filter log score lower than both baselines",
            f"filter {fmt(ls['madkhal']['mean'])}, alert_means_bloom {fmt(ls['alert_means_bloom']['mean'])}, persistence {fmt(ls['persistence']['mean'])}",
            ls["madkhal"]["mean"] < ls["alert_means_bloom"]["mean"]
            and ls["madkhal"]["mean"] < ls["persistence"]["mean"],
        )
        cov = e1["coverage90"]["mean"]
        add("PR-E1-3", "90 percent interval coverage at least 0.85", f"{fmt(cov)}", cov >= 0.85)
        rb = e1["reliability_bins_ok"]
        n50, ok = rb["bins_with_50_days"], rb["bins_within_0_1"]
        add(
            "PR-E1-4",
            "At least 80 percent of reliability bins (50 or more days) within 0.1",
            f"{ok} of {n50} bins",
            n50 > 0 and ok / n50 >= 0.8,
        )
    e2 = res.get("e2")
    if e2:
        pol = e2["policies"]

        def mm(p: str, k: str) -> float:
            return float(pol[p]["metrics"][k]["mean"])

        def rg(p: str, r: R = pol) -> float:
            return float(r[p]["regret_cu"]["mean"])

        add(
            "PR-E2-1",
            "P3 forced shutdowns at most half of P0's",
            f"P3 {fmt(mm('P3', 'forced_shutdowns'))}, P0 {fmt(mm('P0', 'forced_shutdowns'))}",
            mm("P3", "forced_shutdowns") <= 0.5 * mm("P0", "forced_shutdowns"),
        )
        u1, u3 = mm("P1", "unserved_m3"), mm("P3", "unserved_m3")
        add(
            "PR-E2-2",
            "P1 unserved water more than 10 times P3's",
            f"P1 {fmt(u1)} m3, P3 {fmt(u3)} m3",
            u1 > 10 * u3,
        )
        add(
            "PR-E2-3",
            "P3 regret lower than P0, P1 and P2",
            f"P3 {fmt(rg('P3'))}, P0 {fmt(rg('P0'))}, P1 {fmt(rg('P1'))}, P2 {fmt(rg('P2'))} CU",
            rg("P3") < min(rg("P0"), rg("P1"), rg("P2")),
        )
        d3 = mm("P3", "derate_days_per_year")
        add("PR-E2-4", "P3 between 5 and 40 DERATE days per year", f"{fmt(d3)}", 5 <= d3 <= 40)
        costs = {p: mm(p, "weighted_cost_cu") for p in POLICIES}
        add(
            "PR-E2-5",
            "Oracle has the lowest mean weighted cost",
            f"oracle {fmt(costs['P5'])} CU; lowest other {fmt(min(v for k, v in costs.items() if k != 'P5'))} CU",
            all(costs["P5"] <= v + 1e-9 for v in costs.values()),
        )
    e3 = res.get("e3")
    if e2 and e3:
        drop = e3["drop"]
        worse = [
            p for p in POLICIES if p != "P5" and drop[p]["regret_g2_cu"] > drop[p]["regret_g1_cu"]
        ]
        add(
            "PR-E3-1",
            "Every policy except the oracle has higher regret on G2 than on G1",
            f"higher on G2: {', '.join(worse) or 'none'}",
            len(worse) == len(POLICIES) - 1,
        )
        r1, r2 = drop["P3"]["regret_g1_cu"], drop["P3"]["regret_g2_cu"]
        add(
            "PR-E3-2",
            "P3 regret on G2 at least 1.5 times its G1 regret",
            f"G1 {fmt(r1)} CU, G2 {fmt(r2)} CU",
            r2 >= 1.5 * r1,
        )
        p2 = e3["policies"]["P2"]["regret_cu"]["mean"]
        add(
            "PR-E3-3",
            "On G2, P3 regret higher than P2 regret (Madkhal loses to the seasonal rule)",
            f"P3 {fmt(r2)} CU, P2 {fmt(p2)} CU",
            r2 > p2,
        )
    e4 = res.get("e4")
    if e4:

        def cell(a: float, c: float) -> R:
            return next(
                g for g in e4["grid"] if g["availability"] == a and g["sortie_cost_cu"] == c
            )

        g = cell(1.0, 1000.0)
        add(
            "PR-E4-1",
            "At availability 1.0 and 1,000 CU, P4 cheaper than P3",
            f"P4 minus P3 {ci(g['p4_minus_p3_cu'])} CU",
            g["p4_minus_p3_cu"]["mean"] < 0,
        )
        be = e4["break_even"]["break_even_cost_cu"]
        add(
            "PR-E4-2",
            "Break even sortie cost at availability 1.0 between 1,000 and 20,000 CU",
            f"{fmt(be)} ({e4['break_even']['note']})",
            be is not None and 1000 <= be <= 20000,
        )
        g2 = cell(0.2, 16000.0)
        add(
            "PR-E4-3",
            "At availability 0.2 and 16,000 CU, INSPECT does not pay",
            f"P4 minus P3 {ci(g2['p4_minus_p3_cu'])} CU",
            g2["p4_minus_p3_cu"]["mean"] >= 0,
        )
        s = g["sorties_per_year"]["mean"]
        add(
            "PR-E4-4",
            "At availability 1.0 and 1,000 CU, between 2 and 60 sorties per year",
            f"{fmt(s)}",
            2 <= s <= 60,
        )
    e5 = res.get("e5")
    if e5:
        top3 = [r["key"] for r in e5["rank_correlation"][:3]]
        add(
            "PR-E5-1",
            "A detector parameter among the top three by rank correlation",
            ", ".join(top3),
            any(k.startswith("detector.") for k in top3),
        )
        plant_rows = [r for r in e5["one_at_a_time"] if r["key"].startswith("plant.")]
        top = plant_rows[0]["key"] if plant_rows else None
        add(
            "PR-E5-2",
            "Largest plant swing is pretreatment capacity, bloom load lower bound or tail index",
            f"{top}",
            top in ("plant.pretreat_capacity", "plant.bloom_load_min", "plant.bloom_tail_alpha"),
        )
    e6 = res.get("e6")
    if e6:
        c3 = e6["policies"]["P3"]["changes_per_30_days"]["mean"]
        c4 = e6["policies"]["P4"]["changes_per_30_days"]["mean"]
        add(
            "PR-E6-1",
            "P3 and P4 change advice at most 2 times per 30 days",
            f"P3 {fmt(c3)}, P4 {fmt(c4)}",
            c3 <= 2 and c4 <= 2,
        )
        d3 = e6["policies"]["P3"]["dwell_compliance"]["mean"]
        d4 = e6["policies"]["P4"]["dwell_compliance"]["mean"]
        add(
            "PR-E6-2",
            "Dwell compliance 100 percent",
            f"P3 {fmt(d3)}, P4 {fmt(d4)}",
            d3 == 1.0 and d4 == 1.0,
        )
    e7 = res.get("e7")
    if e7:
        burden = {s: v["quiet_non_go_per_year"] for s, v in e7["sites"].items()}
        add(
            "PR-E7-1",
            "Non GO days per year on held out quiet days at most 15 at every site",
            ", ".join(f"{s} {fmt(v)}" for s, v in burden.items()),
            all(v is not None and v <= 15 for v in burden.values()),
        )
        k = _point(e7, "kalba", "E2018-KALBA", "t_ref", 3)
        add(
            "PR-E7-2",
            "Kalba 2018, 3 days before t_ref: not GO (not blind)",
            f"{k['action']} {k['scale']}" if k else "missing",
            bool(k and k.get("action") not in (None, "GO")),
        )
        b18 = _point(e7, "barka", "E2018-BARKA", "t_ref", 3)
        b23 = _point(e7, "barka", "E2023-BARKA", "t_ref", 3)
        add(
            "PR-E7-3",
            "Barka 2018 and 2023, 3 days before t_ref: GO",
            f"2018 {b18.get('action') if b18 else 'missing'}, 2023 {b23.get('action') if b23 else 'missing'}",
            bool(b18 and b23 and b18.get("action") == "GO" and b23.get("action") == "GO"),
        )
        ar = [
            p
            for p in e7["sites"]["alraha"]["points"]
            if p["event_id"] == "E2023-ALRAHA" and "action" in p
        ]
        add(
            "PR-E7-4",
            "Al Raha 2023: GO at every point before the dates",
            ", ".join(f"{p['anchor']} minus {p['days_before']}: {p['action']}" for p in ar),
            bool(ar) and all(p["action"] == "GO" for p in ar),
        )
    return out


METRIC_ROWS = [
    ("weighted_cost_cu", "Weighted cost (CU, secondary view)"),
    ("unserved_m3", "Unserved water (m3 per 2 years)"),
    ("forced_shutdowns", "Forced shutdowns (per 2 years)"),
    ("cleanings", "Cleaning events (per 2 years)"),
    ("membrane_index", "Membrane life used (index)"),
    ("park_days_per_year", "PARK days per year"),
    ("derate_days_per_year", "DERATE days per year"),
    ("escalation_days_per_year", "Escalation days per year"),
    ("changes_per_30_days", "Advice changes per 30 days"),
    ("sorties_per_year", "Survey sorties per year"),
]


def _policy_table(block: R) -> list[str]:
    head = "| Metric | " + " | ".join(f"{p} {POLICY_NAMES[p]}" for p in POLICIES) + " |"
    lines = [head, "|---|" + "---|" * len(POLICIES)]
    for key, label in METRIC_ROWS:
        cells = [ci(block["policies"][p]["metrics"][key]) for p in POLICIES]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append(
        "| Regret versus oracle (CU) | "
        + " | ".join(ci(block["policies"][p]["regret_cu"]) for p in POLICIES)
        + " |"
    )
    return lines


def render(res: dict[str, R], notes: dict[str, str] | None = None) -> str:
    nt = notes or {}
    preds = predictions(res)
    hits = sum(1 for p in preds if p["result"] == "HIT")
    run = res.get("run", {})
    L: list[str] = [
        "# Evaluation",
        "",
        "Generated by `madkhal docs build` from `results/*.json` (written by `madkhal eval`). Do not",
        "edit by hand: a test fails if this file differs from a fresh rendering of the results.",
        "",
        "E1 to E6 run on SYNTHETIC worlds (generators G1 and G2) with a HYPOTHETICAL plant; costs are",
        "in hypothetical cost units (CU). E7 is a REPLAY of real satellite evidence against a",
        "hypothetical plant and makes no claim about any real plant. Every prediction was committed",
        "in `docs/PREREGISTRATION.md` before these results existed.",
        "",
        f"Run: {len(run.get('seeds', []))} evaluation seeds, {run.get('workers', '?')} worker processes, "
        f"{fmt(run.get('seconds_total'))} seconds in total; {run.get('lab_draws', '?')} parameter draws in the lab.",
        "",
        f"## Predictions: {hits} hits of {len(preds)}",
        "",
        "| ID | Prediction | Observed | Result |",
        "|---|---|---|---|",
    ]
    for p in preds:
        L.append(f"| {p['id']} | {p['prediction']} | {p['observed']} | {p['result']} |")
    misses = [p for p in preds if p["result"] == "MISS"]
    L += ["", "Misses are kept and discussed below; none was hidden or re-scored.", ""]
    e1 = res.get("e1")
    if e1:
        L += [
            "## E1 Estimator quality (G1)",
            "",
            "P(bloom at the intake within 3 days). Means over seeds with 95 percent intervals.",
            "",
            "| Score | Filter | alert_means_bloom | persistence |",
            "|---|---|---|---|",
            "| Brier (lower is better) | "
            + " | ".join(
                ci(e1["brier"][m]) for m in ("madkhal", "alert_means_bloom", "persistence")
            )
            + " |",
            "| Log score (lower is better) | "
            + " | ".join(
                ci(e1["log_score"][m]) for m in ("madkhal", "alert_means_bloom", "persistence")
            )
            + " |",
            "",
            f"Coverage of the 90 percent interval of the true parameter probability: {ci(e1['coverage90'])}.",
            "",
            "Reliability (all seeds pooled):",
            "",
            "| Forecast bin | Days | Mean forecast | Observed frequency |",
            "|---|---|---|---|",
        ]
        for b in e1["reliability"]:
            if b["n"] > 0:
                L.append(
                    f"| {fmt(b['bin_lo'], 2)} to {fmt(b['bin_hi'], 2)} | {int(b['n'])} | {fmt(b['mean_forecast'])} | {fmt(b['observed'])} |"
                )
        L.append("")
    for key, title in (("e2", "E2 Policy comparison (G1)"), ("e3", "E3 Robustness (G2, stress)")):
        blk = res.get(key)
        if blk:
            L += [
                f"## {title}",
                "",
                "Means over seeds with 95 percent intervals; every metric reported separately.",
                "",
            ]
            L += _policy_table(blk)
            L += [
                "",
                "Weight sensitivity: regret ranking of P0 to P4 when one weight is halved or doubled (the oracle is not re optimised).",
                "",
                "| Change | Ranking (lowest regret first) |",
                "|---|---|",
            ]
            for name, s in blk["weight_sensitivity"].items():
                L.append(f"| {name} | {', '.join(s['ranking'])} |")
            L.append("")
    pairs = (("P3", "P0"), ("P3", "P1"), ("P3", "P2"), ("P4", "P3"))
    for key, gen in (("e2", "G1"), ("e3", "G2")):
        blk = res.get(key)
        if blk:
            L += [
                f"### Paired regret differences on {gen}",
                "",
                "95 percent interval of the per seed difference. A negative difference favours the",
                "first policy; an interval that includes zero means the ordering is not established.",
                "",
                "| Comparison | Mean difference (CU) | Interval (CU) | Seeds |",
                "|---|---|---|---|",
            ]
            for a, b in pairs:
                d = paired(
                    blk["policies"][a]["regret_per_seed"], blk["policies"][b]["regret_per_seed"]
                )
                L.append(
                    f"| {a} minus {b} | {fmt(d['mean'])} | {fmt(d['lo'])} to {fmt(d['hi'])} | {int(d['n'])} |"
                )
            L.append("")
    e3 = res.get("e3")
    if e3:
        L += [
            "### G1 to G2 change in regret",
            "",
            "| Policy | Regret G1 (CU) | Regret G2 (CU) | Change (CU) |",
            "|---|---|---|---|",
        ]
        for pol in POLICIES:
            d = e3["drop"][pol]
            L.append(
                f"| {pol} {POLICY_NAMES[pol]} | {fmt(d['regret_g1_cu'])} | {fmt(d['regret_g2_cu'])} | {fmt(d['regret_change_cu'])} |"
            )
        L.append("")
    e4 = res.get("e4")
    if e4:
        L += [
            "## E4 Value of inspection (G1)",
            "",
            f"Seeds: {len(e4['seeds'])} (stated reduction). P3 cost without surveys: {ci(e4['p3_cost_cu'])} CU.",
            "",
            "| Availability | Sortie cost (CU) | P4 minus P3 (CU) | Sorties per year |",
            "|---|---|---|---|",
        ]
        for g in e4["grid"]:
            L.append(
                f"| {fmt(g['availability'])} | {fmt(g['sortie_cost_cu'])} | {ci(g['p4_minus_p3_cu'])} | {ci(g['sorties_per_year'])} |"
            )
        be = e4["break_even"]
        L += [
            "",
            f"Break even sortie cost at availability 1.0: {fmt(be['break_even_cost_cu'])} ({be['note']}).",
            "",
        ]
    e5 = res.get("e5")
    if e5:
        L += [
            "## E5 Sensitivity (G1)",
            "",
            "One at a time (plus and minus one spread), mean regret of P3 over the oracle:",
            "",
            "| Parameter | Regret plus (CU) | Regret minus (CU) | Swing (CU) |",
            "|---|---|---|---|",
        ]
        for r in e5["one_at_a_time"]:
            L.append(
                f"| `{r['key']}` | {fmt(r['regret_plus_cu'])} | {fmt(r['regret_minus_cu'])} | {fmt(r['swing_cu'])} |"
            )
        L += [
            "",
            f"Random design ({e5['random_design_samples']} samples), Spearman rank correlation with P3 regret:",
            "",
            "| Parameter | Rank correlation |",
            "|---|---|",
        ]
        for r in e5["rank_correlation"]:
            L.append(f"| `{r['key']}` | {fmt(r['spearman'])} |")
        L += ["", f"Measure this first: {', '.join(e5['measure_first'])}.", ""]
    e6 = res.get("e6")
    if e6:
        L += [
            "## E6 Stability (G1)",
            "",
            "| Policy | Changes per 30 days | Dwell compliance |",
            "|---|---|---|",
        ]
        for p, v in e6["policies"].items():
            L.append(f"| {p} | {ci(v['changes_per_30_days'])} | {ci(v['dwell_compliance'])} |")
        L += ["", e6["note"], ""]
    e7 = res.get("e7")
    if e7:
        L += [
            f"## E7 {e7['label']}",
            "",
            "No performance claim. Non GO advisory days on real evidence:",
            "",
            "| Site | Held out quiet days | Non GO on them | Per year | Days outside event windows | Non GO on them | Per year |",
            "|---|---|---|---|---|---|---|",
        ]
        for s, v in e7["sites"].items():
            L.append(
                f"| {s} | {v['quiet_days']} | {v['quiet_non_go_days']} | {fmt(v['quiet_non_go_per_year'])} | "
                f"{v['outside_windows_days']} | {v['outside_windows_non_go_days']} | {fmt(v['outside_windows_non_go_per_year'])} |"
            )
        L += [
            "",
            "Advisory and belief before each documented event (median P(any bloom) and P(at the intake within 3 days)):",
            "",
            "| Event | Status | Anchor | Days before | Date | Advice | P(any bloom) | P(within 3 days) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for v in e7["sites"].values():
            for p in v["points"]:
                if "action" in p:
                    adv = p["action"] if p["action"] != "DERATE" else f"DERATE {p['scale']}"
                    L.append(
                        f"| {p['label']} | {p['status_badge']} | {p['anchor']} | {p['days_before']} | {p['date']} | {adv} | "
                        f"{fmt(p['p_any_bloom'][1])} | {fmt(p['within_3'][1])} |"
                    )
                else:
                    L.append(
                        f"| {p['label']} | {p['status_badge']} | {p['anchor']} | {p['days_before']} | {p['date']} | {p['note']} | | |"
                    )
        L.append("")
    L += ["## Misses", ""]
    if misses:
        for p in misses:
            L.append(f'* {p["id"]}: predicted "{p["prediction"]}"; observed {p["observed"]}.')
            if p["id"] in nt:
                L.append(f"  {nt[p['id']]}")
    else:
        L.append("None.")
    qualified = [p for p in preds if p["result"] == "HIT" and p["id"] in nt]
    if qualified:
        L += ["", "## Hits that need qualifying", ""]
        for p in qualified:
            L.append(f"* {p['id']}: {nt[p['id']]}")
    L += [
        "",
        "## What these results do not show",
        "",
        "* The plant is hypothetical; no result here says anything about a real plant.",
        "* G1 shares the estimator's assumptions, so E1 and E2 are optimistic by construction; G2 is",
        "  the stress test, and it is still written by the same author.",
        "* The hit rate rests on one detected event, and event dates are mostly upper bounds.",
        "* Costs are hypothetical units; the weight sensitivity shows how rankings move with them.",
        "* Nothing here is validated against a real plant or real operator logs.",
        "* Intervals are mean plus or minus 1.96 standard errors, as preregistered; for skewed,",
        "  mostly zero counts they can extend below zero, which no count can reach.",
        "",
    ]
    return "\n".join(L)


Loader = Callable[[str], R | None]
