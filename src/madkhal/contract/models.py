"""L0 contract models: the single source of truth for every layer and the web app.

JSON Schema, the TypeScript types and the field dictionary are generated from these
models (``madkhal docs build``). Every field carries an English and an Arabic
description; the Arabic is machine drafted and should be reviewed by a native speaker.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .units import Fraction, NonNegative, Percent, Probability, UtcDatetime, fd

SIMULATION_NOTICE = (
    "For simulation and review only. Real flights need the operator's own safety case "
    "and the regulator's approval."
)
BANNER_EVIDENCE = "Evidence: real satellite history from the Nadhir hindcast."
BANNER_HYPOTHETICAL = "Plant, drone and consequences: hypothetical, synthetic parameters."
REPLAY_LABEL = "REPLAY: real satellite evidence, hypothetical plant"
ADVISORY_SCOPE = (
    "Advisory software for planning and learning. It controls nothing and has no "
    "connection to any plant system."
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------- enumerations
class CoverageState(StrEnum):
    """Whether the satellite saw the watch zone on a day."""

    clear = "clear"
    nodata = "nodata"


class DetectorState(StrEnum):
    """Daily state reported by the frozen Nadhir detector."""

    NODATA = "NODATA"
    QUIET = "QUIET"
    EXCEED = "EXCEED"
    ALERT = "ALERT"


class BloomState(StrEnum):
    """Latent bloom state of the estimator."""

    clear = "clear"
    developing = "developing"
    at_intake = "at_intake"


class EvidenceLevel(StrEnum):
    """How far a parameter or decision can be trusted (from Dhill)."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class ParamSource(StrEnum):
    """Where a parameter value comes from."""

    assumption = "assumption"
    literature = "literature"
    nadhir = "nadhir"
    field_calibrated = "field_calibrated"
    validated = "validated"


class ActionKind(StrEnum):
    """Advisory action, ordered from most to least permissive."""

    GO = "GO"
    DERATE = "DERATE"
    PARK = "PARK"
    NO_SAFE_OPTION_ESCALATE = "NO_SAFE_OPTION_ESCALATE"


class StatusClass(StrEnum):
    """Coarse class of a Nadhir evidence status, used for labels."""

    VERIFIED_PRIMARY = "VERIFIED-PRIMARY"
    VERIFIED_SECONDARY = "VERIFIED-SECONDARY"
    UNVERIFIED = "UNVERIFIED"


class Dataset(StrEnum):
    """Which frozen Nadhir detector produced the evidence."""

    olci_v1 = "olci_v1"
    modis_v1 = "modis_v1"


EVIDENCE_LEVEL_TEXT = {
    EvidenceLevel.L0: "L0: uncalibrated (assumptions and illustrative values)",
    EvidenceLevel.L1: "L1: parameterised from a datasheet or the literature",
    EvidenceLevel.L2: "L2: calibrated on field data from the plant",
    EvidenceLevel.L3: "L3: independently validated",
}

# Minimum relative spread by source: measured small, assumption large (Dhill ADR 0003).
MIN_REL_SPREAD = {
    ParamSource.assumption: 0.25,
    ParamSource.literature: 0.05,
    ParamSource.nadhir: 0.0,
    ParamSource.field_calibrated: 0.0,
    ParamSource.validated: 0.0,
}


# ---------------------------------------------------------------- evidence (L1)
class Site(Model):
    """A place with satellite evidence. Coordinates are estimated, never surveyed."""

    id: str = fd("Site identifier used by Nadhir.", "معرّف الموقع كما في نذير.")
    name: str = fd("Place name in English.", "اسم المكان بالإنجليزية.")
    name_ar: str = fd("Place name in Arabic.", "اسم المكان بالعربية.")
    dataset: Dataset = fd(
        "Frozen detector that covers this site.", "الكاشف المجمّد الذي يغطي هذا الموقع."
    )
    lat: float = fd(
        "Latitude of the estimated intake position.",
        "خط العرض لموقع المأخذ المقدّر.",
        "deg",
        ge=-90,
        le=90,
    )
    lon: float = fd(
        "Longitude of the estimated intake position.",
        "خط الطول لموقع المأخذ المقدّر.",
        "deg",
        ge=-180,
        le=180,
    )
    coord_status: str = fd(
        "Status of the coordinates (ESTIMATED in every case).",
        "حالة الإحداثيات (مقدّرة في كل الحالات).",
    )
    offshore_bearing_deg: float = fd(
        "Assumed bearing from the intake towards open water, used only to draw survey missions.",
        "الاتجاه المفترض من المأخذ نحو المياه المفتوحة، يُستخدم فقط لرسم مهام المسح.",
        "deg",
        ge=0,
        lt=360,
    )
    first_date: dt.date = fd("First day of evidence.", "أول يوم في الأدلة.")
    last_date: dt.date = fd("Last day of evidence.", "آخر يوم في الأدلة.")
    radii_km: list[int] = fd(
        "Watch zone radii available.", "أنصاف أقطار مناطق المراقبة المتاحة.", "km"
    )
    primary_radius_km: int = fd(
        "Watch zone radius used by default.", "نصف قطر منطقة المراقبة الافتراضي.", "km"
    )


class EvidenceDay(Model):
    """One day of satellite evidence for one site and watch zone radius."""

    date: dt.date = fd("Calendar day (UTC).", "اليوم التقويمي (بالتوقيت العالمي).")
    site: str = fd("Site identifier.", "معرّف الموقع.")
    radius_km: int = fd("Watch zone radius.", "نصف قطر منطقة المراقبة.", "km")
    coverage: CoverageState = fd(
        "clear when the satellite had a usable view of the zone, nodata otherwise.",
        "صافٍ عندما كانت للقمر الصناعي رؤية صالحة للمنطقة، ولا بيانات خلاف ذلك.",
    )
    alert: bool = fd(
        "Whether the frozen detector was in alert.", "هل كان الكاشف المجمّد في حالة إنذار."
    )
    detector_state: DetectorState = fd(
        "Detector state as written by Nadhir.", "حالة الكاشف كما كتبها نذير."
    )
    anomaly_fraction: Fraction | None = fd(
        "Share of observed pixels that were anomalous, if observed.",
        "نسبة البكسلات المرصودة التي كانت شاذة، إن وُجد رصد.",
        "1",
        default=None,
    )
    source_file: str = fd("Snapshot file the row came from.", "ملف اللقطة الذي جاء منه السطر.")
    source_row: int = fd(
        "Data row number in the source file (1 based).",
        "رقم سطر البيانات في الملف المصدر (يبدأ من 1).",
        ge=1,
    )

    @model_validator(mode="after")
    def _consistent(self) -> EvidenceDay:
        if self.coverage == CoverageState.nodata and self.anomaly_fraction is not None:
            raise ValueError("a nodata day cannot carry an anomaly fraction")
        return self


class Event(Model):
    """A documented bloom related event, with its Nadhir evidence status kept verbatim."""

    id: str = fd("Nadhir event identifier.", "معرّف الحدث في نذير.")
    label: str = fd(
        "Neutral label: place, year and kind. Names no operator.",
        "وصف محايد: المكان والسنة والنوع، دون ذكر أي مشغّل.",
    )
    site: str = fd("Site identifier of the nearest evidence zone.", "معرّف موقع أقرب منطقة أدلة.")
    dataset: Dataset = fd("Detector that can score the event.", "الكاشف القادر على تقييم الحدث.")
    lat: float = fd("Latitude (estimated).", "خط العرض (مقدّر).", "deg")
    lon: float = fd("Longitude (estimated).", "خط الطول (مقدّر).", "deg")
    coord_status: str = fd("Coordinate status from Nadhir.", "حالة الإحداثيات من نذير.")
    date_precision: str = fd("Precision of the documented date.", "دقة التاريخ الموثّق.")
    t_ref: dt.date | None = fd(
        "Reference date (usually a report date, an upper bound on onset).",
        "التاريخ المرجعي (غالبًا تاريخ تقرير، وهو حد أعلى لبداية الأثر).",
        default=None,
    )
    t_ref_earliest: dt.date | None = fd(
        "Earliest date consistent with the sources.", "أبكر تاريخ يتّسق مع المصادر.", default=None
    )
    period_start: dt.date | None = fd(
        "Start of a documented period, for period events.",
        "بداية فترة موثّقة لأحداث الفترات.",
        default=None,
    )
    period_end: dt.date | None = fd(
        "End of a documented period, for period events.",
        "نهاية فترة موثّقة لأحداث الفترات.",
        default=None,
    )
    evaluation: str = fd("How Nadhir scored the event.", "كيف قيّم نذير الحدث.")
    evidence_status: str = fd(
        "Evidence status copied verbatim from Nadhir.", "حالة الأدلة منقولة حرفيًا من نذير."
    )
    status_class: StatusClass = fd(
        "Coarse class of the evidence status.", "الفئة العامة لحالة الأدلة."
    )
    status_badge: str = fd(
        "Short status label shown with the event; it says UNVERIFIED whenever any part is unverified.",
        "وصف مختصر للحالة يُعرض مع الحدث، ويذكر غير موثّق كلما كان أي جزء غير موثّق.",
    )
    species: str | None = fd(
        "Species as stated by Nadhir, if any.", "النوع كما ذكره نذير، إن وُجد.", default=None
    )
    source_file: str = fd("Snapshot file the event came from.", "ملف اللقطة الذي جاء منه الحدث.")
    source_index: int = fd(
        "Position of the event in the source file (1 based).",
        "ترتيب الحدث في الملف المصدر (يبدأ من 1).",
        ge=1,
    )

    @model_validator(mode="after")
    def _unverified_is_labelled(self) -> Event:
        if "UNVERIFIED" in self.evidence_status and "UNVERIFIED" not in self.status_badge:
            raise ValueError("an event with an UNVERIFIED status must say so in its badge")
        return self


class RateWithCounts(Model):
    """A rate that always travels with its counts."""

    k: int = fd("Numerator count.", "العدد في البسط.", ge=0)
    n: int = fd("Denominator count.", "العدد في المقام.", ge=0)
    rate: Probability | None = fd(
        "k / n, absent when n is zero.", "ناتج k / n، ويغيب عندما يكون n صفرًا.", "1", default=None
    )
    note: str = fd("What the counts mean.", "معنى الأعداد.", default="")

    @model_validator(mode="after")
    def _counts(self) -> RateWithCounts:
        if self.k > self.n:
            raise ValueError("k cannot exceed n")
        expected = None if self.n == 0 else self.k / self.n
        if (expected is None) != (self.rate is None) or (
            expected is not None and self.rate is not None and abs(expected - self.rate) > 1e-9
        ):
            raise ValueError("rate must equal k / n")
        return self


class TrackRow(Model):
    """Outcome of the detector for one dated event, cited to its source row."""

    event_id: str = fd("Event identifier.", "معرّف الحدث.")
    label: str = fd("Neutral event label.", "وصف الحدث المحايد.")
    dataset: Dataset = fd("Detector used.", "الكاشف المستخدم.")
    outcome: Literal["DETECTED", "MISSED", "NOT_OBSERVABLE"] = fd(
        "Detected, missed, or not observable (too few clear days before the reference date).",
        "مكتشف، أو فائت، أو غير قابل للرصد (أيام صافية قليلة جدًا قبل التاريخ المرجعي).",
    )
    nadhir_outcome: str = fd("Outcome string written by Nadhir.", "نص النتيجة كما كتبه نذير.")
    clear_days_in_lookback: int = fd(
        "Clear days in the lookback window.", "الأيام الصافية في نافذة الاسترجاع.", "d", ge=0
    )
    days_in_lookback: int = fd(
        "Days in the lookback window.", "عدد أيام نافذة الاسترجاع.", "d", ge=0
    )
    lead_alert_days: float | None = fd(
        "Days from first alert to the reference date.",
        "الأيام من أول إنذار حتى التاريخ المرجعي.",
        "d",
        default=None,
    )
    lead_alert_min_days: float | None = fd(
        "Lead time against the earliest date.",
        "زمن الإنذار المسبق مقابل أبكر تاريخ.",
        "d",
        default=None,
    )
    evidence_status: str = fd("Evidence status (verbatim).", "حالة الأدلة (حرفيًا).")
    status_class: StatusClass = fd(
        "Coarse class of the evidence status.", "الفئة العامة لحالة الأدلة."
    )
    source_file: str = fd("Source file.", "الملف المصدر.")
    source_row: int = fd(
        "Data row in the source file (1 based).", "سطر البيانات في الملف المصدر (يبدأ من 1).", ge=1
    )


class FalseAlarmRow(Model):
    """Held out false alarm counts for one site, copied from Nadhir."""

    site: str = fd("Site identifier.", "معرّف الموقع.")
    dataset: Dataset = fd("Detector used.", "الكاشف المستخدم.")
    radius_km: int = fd("Watch zone radius.", "نصف قطر منطقة المراقبة.", "km")
    alert_days: RateWithCounts = fd(
        "Alert days over clear quiet days in held out years.",
        "أيام الإنذار من بين الأيام الصافية الهادئة في السنوات المحجوزة.",
    )
    episodes: int = fd(
        "Alert episodes started in held out quiet days.",
        "نوبات الإنذار التي بدأت في الأيام الهادئة المحجوزة.",
        ge=0,
    )
    quiet_days: int = fd(
        "Calendar days in the held out quiet set.",
        "الأيام التقويمية في المجموعة الهادئة المحجوزة.",
        "d",
        ge=0,
    )
    episodes_per_year: float = fd(
        "Alert episodes per 365 days (an upper bound on false alarms).",
        "نوبات الإنذار لكل 365 يومًا (حد أعلى للإنذارات الكاذبة).",
        ge=0,
    )
    source_file: str = fd("Source file.", "الملف المصدر.")
    source_row: int = fd(
        "Data row in the source file (1 based).", "سطر البيانات في الملف المصدر (يبدأ من 1).", ge=1
    )


class TrackRecord(Model):
    """Detector track record, small sample shown as small."""

    n_dated: int = fd(
        "Dated disruptions scored by Nadhir.", "الاضطرابات المؤرخة التي قيّمها نذير.", ge=0
    )
    n_observable: int = fd("Of those, how many were observable.", "منها، كم كان قابلًا للرصد.", ge=0)
    n_detected: int = fd(
        "Of the observable, how many were detected.", "من القابلة للرصد، كم اكتُشف.", ge=0
    )
    n_missed: int = fd("Observable but missed.", "قابلة للرصد لكنها فاتت.", ge=0)
    n_not_observable: int = fd(
        "Not observable (satellite blind).", "غير قابلة للرصد (القمر الصناعي أعمى).", ge=0
    )
    hit_rate: RateWithCounts = fd("Detected over observable.", "المكتشف من بين القابل للرصد.")
    observable_rule: str = fd(
        "Rule used to call an event observable.", "القاعدة المستخدمة لاعتبار الحدث قابلًا للرصد."
    )
    rows: list[TrackRow] = fd("One row per dated event.", "سطر لكل حدث مؤرخ.")
    false_alarms: list[FalseAlarmRow] = fd(
        "Held out false alarm rows.", "سطور الإنذارات الكاذبة المحجوزة."
    )
    blind_spot_note: str = fd(
        "The documented species level blind spot.", "النقطة العمياء الموثّقة على مستوى النوع."
    )


# ---------------------------------------------------------------- estimator (L2)
class Interval(Model):
    """Posterior median with an equal tailed credible interval."""

    median: float = fd("Posterior median.", "الوسيط اللاحق.")
    lo: float = fd("Lower bound of the credible interval.", "الحد الأدنى لفترة الموثوقية.")
    hi: float = fd("Upper bound of the credible interval.", "الحد الأعلى لفترة الموثوقية.")
    level: Probability = fd("Credible level, for example 0.9.", "مستوى الموثوقية، مثل 0.9.", "1")

    @model_validator(mode="after")
    def _ordered(self) -> Interval:
        if not self.lo <= self.median <= self.hi:
            raise ValueError("interval must satisfy lo <= median <= hi")
        return self


class HorizonProbability(Model):
    """P(at_intake at any time within the horizon)."""

    horizon_days: int = fd("Forecast horizon.", "أفق التنبؤ.", "d", ge=0, le=30)
    p_at_intake: Interval = fd("Probability with interval.", "الاحتمال مع فترة الموثوقية.")


class BeliefParameter(Model):
    """A detector or transition parameter used by the estimator, with its posterior."""

    key: str = fd("Parameter key.", "مفتاح المعامل.")
    label: str = fd("Plain language name.", "اسم بلغة بسيطة.")
    value: Interval = fd("Posterior summary over draws.", "ملخص التوزيع اللاحق عبر السحبات.")
    source: ParamSource = fd("Where the value comes from.", "مصدر القيمة.")
    provenance: str = fd("Counts or reasoning behind the value.", "الأعداد أو المنطق وراء القيمة.")


class BloomBelief(Model):
    """The estimator's belief for one site and day."""

    site: str = fd("Site identifier.", "معرّف الموقع.")
    date: dt.date = fd(
        "Day of the belief (end of day, UTC).", "يوم الاعتقاد (نهاية اليوم، بالتوقيت العالمي)."
    )
    p_clear: Interval = fd("P(clear).", "احتمال الحالة الصافية.")
    p_developing: Interval = fd(
        "P(developing in the watch zone, not at the intake).",
        "احتمال تطوّر الازدهار في منطقة المراقبة دون بلوغ المأخذ.",
    )
    p_at_intake: Interval = fd("P(bloom at the intake).", "احتمال وجود الازدهار عند المأخذ.")
    p_any_bloom: Interval = fd(
        "P(developing or at the intake).", "احتمال التطوّر أو الوجود عند المأخذ."
    )
    within: list[HorizonProbability] = fd(
        "P(at_intake within 1, 3 and 7 days).", "احتمال بلوغ المأخذ خلال 1 و3 و7 أيام."
    )
    staleness_days: int | None = fd(
        "Days since the last clear satellite observation (absent if none yet).",
        "الأيام منذ آخر رصد صافٍ بالقمر الصناعي (يغيب إن لم يوجد بعد).",
        "d",
        default=None,
    )
    observation: CoverageState = fd("Coverage on this day.", "التغطية في هذا اليوم.")
    alert: bool = fd("Detector alert on this day.", "إنذار الكاشف في هذا اليوم.")
    n_draws: int = fd(
        "Posterior parameter draws used.", "عدد سحبات المعاملات اللاحقة المستخدمة.", ge=1
    )
    seed: int = fd("Seed of the parameter draws.", "بذرة سحبات المعاملات.", ge=0)
    parameters: list[BeliefParameter] = fd(
        "Parameters used, with posteriors.", "المعاملات المستخدمة مع توزيعاتها اللاحقة."
    )


# ---------------------------------------------------------------- plant (L3)
class Parameter(Model):
    """A model parameter with provenance. The evidence level is required."""

    key: str = fd("Parameter key.", "مفتاح المعامل.")
    label: str = fd("Plain language name.", "اسم بلغة بسيطة.")
    value: float = fd("Nominal value.", "القيمة الاسمية.")
    unit: str = fd("Unit of the value.", "وحدة القيمة.")
    evidence_level: EvidenceLevel = fd(
        "Evidence level of this parameter.", "مستوى الأدلة لهذا المعامل."
    )
    source: ParamSource = fd("Where the value comes from.", "مصدر القيمة.")
    provenance: str = fd("Reasoning or citation behind the value.", "المنطق أو المرجع وراء القيمة.")
    rel_spread: NonNegative = fd(
        "Relative spread (one standard deviation on the log scale).",
        "الانتشار النسبي (انحراف معياري واحد على المقياس اللوغاريتمي).",
        "1",
    )
    adverse: Literal["up", "down"] = fd(
        "Direction in which the parameter makes outcomes worse.",
        "الاتجاه الذي يجعل فيه المعامل النتائج أسوأ.",
    )

    @model_validator(mode="after")
    def _spread_follows_provenance(self) -> Parameter:
        floor = MIN_REL_SPREAD[self.source]
        if self.rel_spread + 1e-12 < floor:
            raise ValueError(
                f"{self.key}: spread {self.rel_spread} below {floor} required for source {self.source}"
            )
        if self.source == ParamSource.assumption and self.evidence_level != EvidenceLevel.L0:
            raise ValueError(f"{self.key}: an assumption can only be evidence level L0")
        return self


class PlantProfile(Model):
    """A hypothetical plant. Every parameter carries an evidence level and provenance."""

    id: str = fd("Profile identifier.", "معرّف الملف التعريفي.")
    name: str = fd("Profile name.", "اسم الملف التعريفي.")
    hypothetical: Literal[True] = fd(
        "Always true: no real plant is modelled.", "صحيح دائمًا: لا تُنمذج أي محطة حقيقية."
    )
    description: str = fd("What the profile represents.", "ما يمثّله الملف التعريفي.")
    parameters: list[Parameter] = fd("All parameters.", "جميع المعاملات.")

    @model_validator(mode="after")
    def _unique(self) -> PlantProfile:
        keys = [p.key for p in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate parameter keys")
        return self

    def param(self, key: str) -> Parameter:
        for p in self.parameters:
            if p.key == key:
                return p
        raise KeyError(key)

    @property
    def assumption_share(self) -> float:
        if not self.parameters:
            return 1.0
        n = sum(1 for p in self.parameters if p.source == ParamSource.assumption)
        return n / len(self.parameters)

    @property
    def evidence_level(self) -> EvidenceLevel:
        return min((p.evidence_level for p in self.parameters), default=EvidenceLevel.L0)


class Limits(Model):
    """Hard limits and risk budgets of the decision."""

    fouling_limit: float = fd(
        "Fouling index hard limit.", "الحد الصارم لمؤشر الانسداد.", "1", default=1.0, gt=0
    )
    fouling_risk_budget: Probability = fd(
        "Largest allowed P(fouling breach) over the horizon.",
        "أكبر احتمال مسموح لتجاوز حد الانسداد خلال الأفق.",
        "1",
        default=0.05,
    )
    water_allowance_m3: NonNegative = fd(
        "Unserved water allowed over the horizon before it counts as a breach.",
        "كمية المياه غير المزوّدة المسموح بها خلال الأفق قبل اعتبارها تجاوزًا.",
        "m3",
        default=0.0,
    )
    water_risk_budget: Probability = fd(
        "Largest allowed P(unserved water above the allowance).",
        "أكبر احتمال مسموح لتجاوز المياه غير المزوّدة الحد المسموح.",
        "1",
        default=0.05,
    )
    horizon_hours: int = fd("Decision horizon.", "أفق القرار.", "h", default=72, ge=6, le=168)
    dwell_hours: float = fd(
        "Minimum time before a less restrictive change.",
        "أقل مدة قبل التحول إلى إجراء أقل تقييدًا.",
        "h",
        default=12.0,
        ge=0,
    )


class PlantState(Model):
    """Current state of the hypothetical plant."""

    fouling_index: NonNegative = fd(
        "Current fouling index (1 is the hard limit).",
        "مؤشر الانسداد الحالي (1 هو الحد الصارم).",
        "1",
        default=0.2,
    )
    storage_hours: NonNegative = fd(
        "Product water in storage, in hours of demand.",
        "المياه المنتجة في الخزان بساعات من الطلب.",
        "h",
        default=18.0,
    )
    current_action: ActionKind = fd("Action in force.", "الإجراء الساري.", default=ActionKind.GO)
    current_scale: Fraction = fd("Flow scale in force.", "مقياس التدفق الساري.", "1", default=1.0)
    hours_in_action: NonNegative = fd(
        "Hours since the action in force began.",
        "الساعات منذ بدء الإجراء الساري.",
        "h",
        default=1000.0,
    )


# ---------------------------------------------------------------- decision (L4)
class CandidateEvaluation(Model):
    """Risk of one candidate action over the horizon."""

    action: ActionKind = fd("Candidate action.", "الإجراء المرشّح.")
    scale: Fraction = fd("Flow scale q.", "مقياس التدفق q.", "1")
    p_fouling_breach: Probability = fd(
        "P(fouling index reaches the limit).", "احتمال بلوغ مؤشر الانسداد الحد.", "1"
    )
    p_water_breach: Probability = fd(
        "P(unserved water above the allowance).",
        "احتمال تجاوز المياه غير المزوّدة الحد المسموح.",
        "1",
    )
    expected_unserved_m3: NonNegative = fd(
        "Expected unserved water.", "المياه غير المزوّدة المتوقعة.", "m3"
    )
    feasible: bool = fd("Both risks within budget.", "كلا الخطرين ضمن الميزانية.")


class ConstraintStatus(Model):
    """How close a constraint is to its budget for the chosen action."""

    name: Literal["fouling", "water_security", "dwell"] = fd("Constraint name.", "اسم القيد.")
    value: float = fd("Current value (probability or hours).", "القيمة الحالية (احتمال أو ساعات).")
    budget: float = fd("Budget or limit.", "الميزانية أو الحد.")
    used_percent: Percent = fd(
        "Share of the budget used, capped at 100.", "نسبة الميزانية المستخدمة، بحد أقصى 100.", "%"
    )


class InspectAssessment(Model):
    """Pre posterior value of a drone survey against its cost."""

    value_cu: NonNegative = fd(
        "Expected reduction in loss from one survey, in cost units (hypothetical).",
        "الانخفاض المتوقع في الخسارة من مسح واحد بوحدات تكلفة افتراضية.",
        "CU",
    )
    sortie_cost_cu: NonNegative = fd(
        "Cost of one sortie (hypothetical).", "تكلفة طلعة واحدة (افتراضية).", "CU"
    )
    break_even_cost_cu: NonNegative = fd(
        "Sortie cost at which the survey just pays.", "تكلفة الطلعة التي يتعادل عندها المسح.", "CU"
    )
    availability: Probability = fd(
        "Probability that weather allows the sortie.", "احتمال أن يسمح الطقس بالطلعة.", "1"
    )
    decision_could_change: bool = fd(
        "Whether some survey outcome changes the best action.",
        "هل يغيّر أي ناتج للمسح الإجراء الأفضل.",
    )
    inspect: bool = fd("INSPECT advisory set.", "تفعيل توصية الفحص.")
    reasons: list[str] = fd("Reasons in plain language.", "الأسباب بلغة بسيطة.")


class Explanation(Model):
    """Structured explanation; the plain language text is rendered from it."""

    belief_summary: dict[str, float] = fd("Belief quantities used.", "كميات الاعتقاد المستخدمة.")
    plant_state: PlantState = fd("Plant state used.", "حالة المحطة المستخدمة.")
    limits: Limits = fd("Limits and budgets used.", "الحدود والميزانيات المستخدمة.")
    candidates: list[CandidateEvaluation] = fd(
        "Every candidate with its risks.", "كل إجراء مرشّح مع مخاطره."
    )
    unconstrained_action: ActionKind = fd(
        "Action before the dwell rule.", "الإجراء قبل قاعدة مدة البقاء."
    )
    unconstrained_scale: Fraction = fd(
        "Scale before the dwell rule.", "المقياس قبل قاعدة مدة البقاء.", "1"
    )
    dwell_held: bool = fd(
        "Whether the dwell rule held a more restrictive action.",
        "هل أبقت قاعدة مدة البقاء على إجراء أكثر تقييدًا.",
    )
    binding_constraint: str | None = fd(
        "Constraint that stops a more permissive action.",
        "القيد الذي يمنع إجراءً أكثر تساهلًا.",
        default=None,
    )
    evidence_level: EvidenceLevel = fd(
        "Evidence level of the plant profile.", "مستوى أدلة ملف المحطة."
    )
    assumption_share: Fraction = fd(
        "Share of plant parameters that are assumptions.",
        "نسبة معاملات المحطة التي هي افتراضات.",
        "1",
    )
    n_samples: int = fd(
        "Monte Carlo samples (posterior draws).", "عينات مونت كارلو (سحبات لاحقة).", ge=1
    )
    inspect: InspectAssessment | None = fd(
        "Survey value assessment, if computed.", "تقييم قيمة المسح إن حُسب.", default=None
    )
    what_would_change: list[str] = fd(
        "Conditions that would change the advisory.", "الظروف التي ستغيّر التوصية."
    )


class PlainText(Model):
    """Three sentences rendered from the explanation."""

    what: str = fd("What to do.", "ما يجب فعله.")
    why: str = fd("Why.", "لماذا.")
    change: str = fd("What would change this.", "ما الذي سيغيّر ذلك.")


class Advisory(Model):
    """An advisory for one site and time. It is advice, never a control action."""

    id: str = fd("Identifier: the inputs hash.", "المعرّف: بصمة المدخلات.")
    site: str = fd("Site identifier.", "معرّف الموقع.")
    issued_for: UtcDatetime = fd(
        "Time the advisory applies to (UTC).", "الوقت الذي تنطبق عليه التوصية (بالتوقيت العالمي)."
    )
    action: ActionKind = fd("Advised action.", "الإجراء الموصى به.")
    scale: Fraction = fd("Advised flow scale q.", "مقياس التدفق الموصى به q.", "1")
    reasons: list[str] = fd("Reasons in plain language.", "الأسباب بلغة بسيطة.")
    binding_constraint: str | None = fd("Binding constraint.", "القيد الحاكم.", default=None)
    p_breach_full_scale: Probability = fd(
        "P(fouling limit reached within the horizon at full scale).",
        "احتمال بلوغ حد الانسداد خلال الأفق عند التشغيل الكامل.",
        "1",
    )
    time_to_limit_hours: float | None = fd(
        "Hours until the limit at full scale at the 95 percent risk quantile (absent if beyond the horizon).",
        "الساعات حتى بلوغ الحد عند التشغيل الكامل عند مئين الخطر 95 (يغيب إن تجاوز الأفق).",
        "h",
        default=None,
    )
    constraints: list[ConstraintStatus] = fd(
        "How close each constraint is.", "مدى قرب كل قيد من حدّه."
    )
    evidence_level: EvidenceLevel = fd("Evidence level of the advisory.", "مستوى أدلة التوصية.")
    assumption_share: Fraction = fd(
        "Share of plant parameters that are assumptions.",
        "نسبة معاملات المحطة التي هي افتراضات.",
        "1",
    )
    inspect: bool = fd("INSPECT advisory (task a survey drone).", "توصية الفحص (تكليف طائرة مسح).")
    inspect_reasons: list[str] = fd("Reasons for or against INSPECT.", "أسباب الفحص أو عدمه.")
    explanation: Explanation = fd("Structured explanation (required).", "شرح منظّم (إلزامي).")
    text: PlainText = fd("Plain language rendering.", "صياغة بلغة بسيطة.")
    inputs_hash: str = fd("SHA-256 of the canonical inputs.", "بصمة SHA-256 للمدخلات المعيارية.")
    seed: int = fd("Seed used.", "البذرة المستخدمة.", ge=0)
    label: str = fd(
        "Context label, for example the replay label.", "وصف السياق، مثل وصف الإعادة.", default=""
    )


# ---------------------------------------------------------------- lab (L5)
class Scenario(Model):
    """A user bloom scenario for the Scenario Lab (synthetic)."""

    site: str = fd(
        "Site whose seasonality and coverage are used.", "الموقع الذي تُستخدم موسميته وتغطيته."
    )
    start_date: dt.date = fd("First day.", "اليوم الأول.")
    days: int = fd("Scenario length.", "طول السيناريو.", "d", ge=3, le=60)
    onset_day: int | None = fd(
        "Day the bloom enters the watch zone (absent for none).",
        "اليوم الذي يدخل فيه الازدهار منطقة المراقبة (يغيب إن لم يوجد).",
        "d",
        default=None,
        ge=0,
    )
    days_to_intake: int = fd(
        "Days from watch zone to intake.",
        "الأيام من منطقة المراقبة إلى المأخذ.",
        "d",
        default=4,
        ge=0,
        le=30,
    )
    duration_days: int = fd(
        "Days the bloom stays at the intake.",
        "الأيام التي يبقى فيها الازدهار عند المأخذ.",
        "d",
        default=10,
        ge=1,
        le=60,
    )
    intensity: float = fd(
        "Bloom load added at the intake, relative to the design load.",
        "حمل الازدهار المضاف عند المأخذ نسبةً إلى حمل التصميم.",
        "1",
        default=1.0,
        ge=0,
        le=10,
    )
    detector_availability: Probability = fd(
        "Share of days with a clear satellite view.",
        "نسبة الأيام ذات الرؤية الصافية.",
        "1",
        default=0.5,
    )
    detector_visible: bool = fd(
        "Whether the bloom is visible to the broadband detector.",
        "هل الازدهار مرئي للكاشف عريض النطاق.",
        default=True,
    )
    seed: int = fd("Seed.", "البذرة.", default=7, ge=0, le=2**31 - 1)


class MetricSummary(Model):
    """Mean of a metric over seeds with a 95 percent interval."""

    mean: float = fd("Mean over seeds.", "المتوسط عبر البذور.")
    lo: float = fd("Lower 95 percent bound of the mean.", "الحد الأدنى 95 بالمئة للمتوسط.")
    hi: float = fd("Upper 95 percent bound of the mean.", "الحد الأعلى 95 بالمئة للمتوسط.")
    unit: str = fd("Unit.", "الوحدة.")
    n: int = fd("Number of seeds.", "عدد البذور.", ge=1)


class PolicyResult(Model):
    """Results of one policy on one generator."""

    policy: str = fd("Policy identifier.", "معرّف السياسة.")
    generator: Literal["G1", "G2"] = fd("Scenario generator.", "مولّد السيناريوهات.")
    n_seeds: int = fd("Seeds run.", "البذور المنفّذة.", ge=1)
    metrics: dict[str, MetricSummary] = fd(
        "Every metric, never collapsed.", "كل مقياس على حدة دون دمج."
    )


# ---------------------------------------------------------------- tasking (L6)
class Waypoint(Model):
    """A mission waypoint."""

    lat: float = fd("Latitude.", "خط العرض.", "deg", ge=-90, le=90)
    lon: float = fd("Longitude.", "خط الطول.", "deg", ge=-180, le=180)
    alt_m: float = fd(
        "Altitude above the take off point.", "الارتفاع فوق نقطة الإقلاع.", "m", ge=0, le=500
    )


class DroneProfile(Model):
    """Hypothetical survey drone."""

    endurance_min: float = fd("Endurance.", "مدة التحمل.", default=25.0, gt=0)
    cruise_speed_ms: float = fd("Cruise speed.", "سرعة الطيران.", "m/s", default=12.0, gt=0)
    reserve_fraction: Fraction = fd(
        "Battery reserve kept back.", "احتياطي البطارية المحفوظ.", "1", default=0.2
    )
    wind_limit_ms: float = fd(
        "Wind speed above which the drone does not fly.",
        "سرعة الرياح التي لا تطير فوقها الطائرة.",
        "m/s",
        default=10.0,
        gt=0,
    )
    altitude_m: float = fd("Survey altitude.", "ارتفاع المسح.", "m", default=90.0, ge=60, le=120)


class Mission(Model):
    """A survey mission. For simulation and review only."""

    id: str = fd("Identifier: the inputs hash.", "المعرّف: بصمة المدخلات.")
    site: str = fd("Site identifier.", "معرّف الموقع.")
    radius_m: float = fd(
        "Survey radius offshore of the intake.", "نصف قطر المسح بعيدًا عن المأخذ.", "m", gt=0
    )
    line_spacing_m: float = fd("Spacing of survey lines.", "المسافة بين خطوط المسح.", "m", gt=0)
    drone: DroneProfile = fd("Drone profile.", "ملف الطائرة.")
    waypoints: list[Waypoint] = fd(
        "Waypoints in order, starting and ending at home.",
        "نقاط الطريق بالترتيب، تبدأ وتنتهي عند نقطة الانطلاق.",
    )
    distance_m: NonNegative = fd("Total path length.", "الطول الكلي للمسار.", "m")
    flight_time_s: NonNegative = fd(
        "Flight time at cruise speed.", "زمن الطيران بسرعة الطيران.", "s"
    )
    usable_time_s: NonNegative = fd("Endurance less reserve.", "التحمل بعد خصم الاحتياطي.", "s")
    feasible: bool = fd("Whether the mission fits the profile.", "هل تتسع المهمة ضمن ملف الطائرة.")
    refused_reason: str | None = fd("Why a mission was refused.", "سبب رفض المهمة.", default=None)
    notice: Literal[
        "For simulation and review only. Real flights need the operator's own safety case and the regulator's approval."
    ] = fd("Simulation only statement (always present).", "بيان المحاكاة فقط (موجود دائمًا).")


CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    Site,
    EvidenceDay,
    Event,
    RateWithCounts,
    TrackRow,
    FalseAlarmRow,
    TrackRecord,
    Interval,
    HorizonProbability,
    BeliefParameter,
    BloomBelief,
    Parameter,
    PlantProfile,
    Limits,
    PlantState,
    CandidateEvaluation,
    ConstraintStatus,
    InspectAssessment,
    Explanation,
    PlainText,
    Advisory,
    Scenario,
    MetricSummary,
    PolicyResult,
    Waypoint,
    DroneProfile,
    Mission,
)

ACTION_ORDER = {
    ActionKind.GO: 0,
    ActionKind.DERATE: 1,
    ActionKind.PARK: 2,
    ActionKind.NO_SAFE_OPTION_ESCALATE: 3,
}


def restrictiveness(action: ActionKind, scale: float) -> float:
    """Total order of restrictiveness: higher means more restrictive.

    GO < DERATE (high scale) < DERATE (low scale) < PARK < NO_SAFE_OPTION_ESCALATE.
    """
    if action == ActionKind.NO_SAFE_OPTION_ESCALATE:
        return 3.0
    if action == ActionKind.PARK:
        return 2.0
    return 1.0 - float(scale)
