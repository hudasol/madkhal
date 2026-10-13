# Field dictionary

Generated from `madkhal.contract.models` by `madkhal docs build`. Do not edit by hand.

The Arabic descriptions are machine drafted and should be reviewed by a native speaker.

Conventions: UTC is stored and Asia/Dubai is used for display; SI units; volumes in m3;
flow in m3/h; percentages 0 to 100; probabilities 0 to 1; costs in hypothetical cost
units (CU).

## Site

A place with satellite evidence. Coordinates are estimated, never surveyed.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `id` | `string` |  | Site identifier used by Nadhir. | معرّف الموقع كما في نذير. |
| `name` | `string` |  | Place name in English. | اسم المكان بالإنجليزية. |
| `name_ar` | `string` |  | Place name in Arabic. | اسم المكان بالعربية. |
| `dataset` | `Dataset` |  | Frozen detector that covers this site. | الكاشف المجمّد الذي يغطي هذا الموقع. |
| `lat` | `number` | deg | Latitude of the estimated intake position. | خط العرض لموقع المأخذ المقدّر. |
| `lon` | `number` | deg | Longitude of the estimated intake position. | خط الطول لموقع المأخذ المقدّر. |
| `coord_status` | `string` |  | Status of the coordinates (ESTIMATED in every case). | حالة الإحداثيات (مقدّرة في كل الحالات). |
| `offshore_bearing_deg` | `number` | deg | Assumed bearing from the intake towards open water, used only to draw survey missions. | الاتجاه المفترض من المأخذ نحو المياه المفتوحة، يُستخدم فقط لرسم مهام المسح. |
| `first_date` | `string` |  | First day of evidence. | أول يوم في الأدلة. |
| `last_date` | `string` |  | Last day of evidence. | آخر يوم في الأدلة. |
| `radii_km` | `Array<number>` | km | Watch zone radii available. | أنصاف أقطار مناطق المراقبة المتاحة. |
| `primary_radius_km` | `number` | km | Watch zone radius used by default. | نصف قطر منطقة المراقبة الافتراضي. |

## EvidenceDay

One day of satellite evidence for one site and watch zone radius.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `date` | `string` |  | Calendar day (UTC). | اليوم التقويمي (بالتوقيت العالمي). |
| `site` | `string` |  | Site identifier. | معرّف الموقع. |
| `radius_km` | `number` | km | Watch zone radius. | نصف قطر منطقة المراقبة. |
| `coverage` | `CoverageState` |  | clear when the satellite had a usable view of the zone, nodata otherwise. | صافٍ عندما كانت للقمر الصناعي رؤية صالحة للمنطقة، ولا بيانات خلاف ذلك. |
| `alert` | `boolean` |  | Whether the frozen detector was in alert. | هل كان الكاشف المجمّد في حالة إنذار. |
| `detector_state` | `DetectorState` |  | Detector state as written by Nadhir. | حالة الكاشف كما كتبها نذير. |
| `anomaly_fraction` | `number \| null` | 1 | Share of observed pixels that were anomalous, if observed. | نسبة البكسلات المرصودة التي كانت شاذة، إن وُجد رصد. |
| `source_file` | `string` |  | Snapshot file the row came from. | ملف اللقطة الذي جاء منه السطر. |
| `source_row` | `number` |  | Data row number in the source file (1 based). | رقم سطر البيانات في الملف المصدر (يبدأ من 1). |

## Event

A documented bloom related event, with its Nadhir evidence status kept verbatim.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `id` | `string` |  | Nadhir event identifier. | معرّف الحدث في نذير. |
| `label` | `string` |  | Neutral label: place, year and kind. Names no operator. | وصف محايد: المكان والسنة والنوع، دون ذكر أي مشغّل. |
| `site` | `string` |  | Site identifier of the nearest evidence zone. | معرّف موقع أقرب منطقة أدلة. |
| `dataset` | `Dataset` |  | Detector that can score the event. | الكاشف القادر على تقييم الحدث. |
| `lat` | `number` | deg | Latitude (estimated). | خط العرض (مقدّر). |
| `lon` | `number` | deg | Longitude (estimated). | خط الطول (مقدّر). |
| `coord_status` | `string` |  | Coordinate status from Nadhir. | حالة الإحداثيات من نذير. |
| `date_precision` | `string` |  | Precision of the documented date. | دقة التاريخ الموثّق. |
| `t_ref` | `string \| null` |  | Reference date (usually a report date, an upper bound on onset). | التاريخ المرجعي (غالبًا تاريخ تقرير، وهو حد أعلى لبداية الأثر). |
| `t_ref_earliest` | `string \| null` |  | Earliest date consistent with the sources. | أبكر تاريخ يتّسق مع المصادر. |
| `period_start` | `string \| null` |  | Start of a documented period, for period events. | بداية فترة موثّقة لأحداث الفترات. |
| `period_end` | `string \| null` |  | End of a documented period, for period events. | نهاية فترة موثّقة لأحداث الفترات. |
| `evaluation` | `string` |  | How Nadhir scored the event. | كيف قيّم نذير الحدث. |
| `evidence_status` | `string` |  | Evidence status copied verbatim from Nadhir. | حالة الأدلة منقولة حرفيًا من نذير. |
| `status_class` | `StatusClass` |  | Coarse class of the evidence status. | الفئة العامة لحالة الأدلة. |
| `species` | `string \| null` |  | Species as stated by Nadhir, if any. | النوع كما ذكره نذير، إن وُجد. |
| `source_file` | `string` |  | Snapshot file the event came from. | ملف اللقطة الذي جاء منه الحدث. |
| `source_index` | `number` |  | Position of the event in the source file (1 based). | ترتيب الحدث في الملف المصدر (يبدأ من 1). |

## RateWithCounts

A rate that always travels with its counts.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `k` | `number` |  | Numerator count. | العدد في البسط. |
| `n` | `number` |  | Denominator count. | العدد في المقام. |
| `rate` | `number \| null` | 1 | k / n, absent when n is zero. | ناتج k / n، ويغيب عندما يكون n صفرًا. |
| `note` | `string` |  | What the counts mean. | معنى الأعداد. |

## TrackRow

Outcome of the detector for one dated event, cited to its source row.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `event_id` | `string` |  | Event identifier. | معرّف الحدث. |
| `label` | `string` |  | Neutral event label. | وصف الحدث المحايد. |
| `dataset` | `Dataset` |  | Detector used. | الكاشف المستخدم. |
| `outcome` | `"DETECTED" \| "MISSED" \| "NOT_OBSERVABLE"` |  | Detected, missed, or not observable (too few clear days before the reference date). | مكتشف، أو فائت، أو غير قابل للرصد (أيام صافية قليلة جدًا قبل التاريخ المرجعي). |
| `nadhir_outcome` | `string` |  | Outcome string written by Nadhir. | نص النتيجة كما كتبه نذير. |
| `clear_days_in_lookback` | `number` | d | Clear days in the lookback window. | الأيام الصافية في نافذة الاسترجاع. |
| `days_in_lookback` | `number` | d | Days in the lookback window. | عدد أيام نافذة الاسترجاع. |
| `lead_alert_days` | `number \| null` | d | Days from first alert to the reference date. | الأيام من أول إنذار حتى التاريخ المرجعي. |
| `lead_alert_min_days` | `number \| null` | d | Lead time against the earliest date. | زمن الإنذار المسبق مقابل أبكر تاريخ. |
| `evidence_status` | `string` |  | Evidence status (verbatim). | حالة الأدلة (حرفيًا). |
| `status_class` | `StatusClass` |  | Coarse class of the evidence status. | الفئة العامة لحالة الأدلة. |
| `source_file` | `string` |  | Source file. | الملف المصدر. |
| `source_row` | `number` |  | Data row in the source file (1 based). | سطر البيانات في الملف المصدر (يبدأ من 1). |

## FalseAlarmRow

Held out false alarm counts for one site, copied from Nadhir.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `site` | `string` |  | Site identifier. | معرّف الموقع. |
| `dataset` | `Dataset` |  | Detector used. | الكاشف المستخدم. |
| `radius_km` | `number` | km | Watch zone radius. | نصف قطر منطقة المراقبة. |
| `alert_days` | `RateWithCounts` |  | Alert days over clear quiet days in held out years. | أيام الإنذار من بين الأيام الصافية الهادئة في السنوات المحجوزة. |
| `episodes` | `number` |  | Alert episodes started in held out quiet days. | نوبات الإنذار التي بدأت في الأيام الهادئة المحجوزة. |
| `quiet_days` | `number` | d | Calendar days in the held out quiet set. | الأيام التقويمية في المجموعة الهادئة المحجوزة. |
| `episodes_per_year` | `number` |  | Alert episodes per 365 days (an upper bound on false alarms). | نوبات الإنذار لكل 365 يومًا (حد أعلى للإنذارات الكاذبة). |
| `source_file` | `string` |  | Source file. | الملف المصدر. |
| `source_row` | `number` |  | Data row in the source file (1 based). | سطر البيانات في الملف المصدر (يبدأ من 1). |

## TrackRecord

Detector track record, small sample shown as small.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `n_dated` | `number` |  | Dated disruptions scored by Nadhir. | الاضطرابات المؤرخة التي قيّمها نذير. |
| `n_observable` | `number` |  | Of those, how many were observable. | منها، كم كان قابلًا للرصد. |
| `n_detected` | `number` |  | Of the observable, how many were detected. | من القابلة للرصد، كم اكتُشف. |
| `n_missed` | `number` |  | Observable but missed. | قابلة للرصد لكنها فاتت. |
| `n_not_observable` | `number` |  | Not observable (satellite blind). | غير قابلة للرصد (القمر الصناعي أعمى). |
| `hit_rate` | `RateWithCounts` |  | Detected over observable. | المكتشف من بين القابل للرصد. |
| `observable_rule` | `string` |  | Rule used to call an event observable. | القاعدة المستخدمة لاعتبار الحدث قابلًا للرصد. |
| `rows` | `Array<TrackRow>` |  | One row per dated event. | سطر لكل حدث مؤرخ. |
| `false_alarms` | `Array<FalseAlarmRow>` |  | Held out false alarm rows. | سطور الإنذارات الكاذبة المحجوزة. |
| `blind_spot_note` | `string` |  | The documented species level blind spot. | النقطة العمياء الموثّقة على مستوى النوع. |

## Interval

Posterior median with an equal tailed credible interval.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `median` | `number` |  | Posterior median. | الوسيط اللاحق. |
| `lo` | `number` |  | Lower bound of the credible interval. | الحد الأدنى لفترة الموثوقية. |
| `hi` | `number` |  | Upper bound of the credible interval. | الحد الأعلى لفترة الموثوقية. |
| `level` | `number` | 1 | Credible level, for example 0.9. | مستوى الموثوقية، مثل 0.9. |

## HorizonProbability

P(at_intake at any time within the horizon).

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `horizon_days` | `number` | d | Forecast horizon. | أفق التنبؤ. |
| `p_at_intake` | `Interval` |  | Probability with interval. | الاحتمال مع فترة الموثوقية. |

## BeliefParameter

A detector or transition parameter used by the estimator, with its posterior.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `key` | `string` |  | Parameter key. | مفتاح المعامل. |
| `label` | `string` |  | Plain language name. | اسم بلغة بسيطة. |
| `value` | `Interval` |  | Posterior summary over draws. | ملخص التوزيع اللاحق عبر السحبات. |
| `source` | `ParamSource` |  | Where the value comes from. | مصدر القيمة. |
| `provenance` | `string` |  | Counts or reasoning behind the value. | الأعداد أو المنطق وراء القيمة. |

## BloomBelief

The estimator's belief for one site and day.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `site` | `string` |  | Site identifier. | معرّف الموقع. |
| `date` | `string` |  | Day of the belief (end of day, UTC). | يوم الاعتقاد (نهاية اليوم، بالتوقيت العالمي). |
| `p_clear` | `Interval` |  | P(clear). | احتمال الحالة الصافية. |
| `p_developing` | `Interval` |  | P(developing in the watch zone, not at the intake). | احتمال تطوّر الازدهار في منطقة المراقبة دون بلوغ المأخذ. |
| `p_at_intake` | `Interval` |  | P(bloom at the intake). | احتمال وجود الازدهار عند المأخذ. |
| `p_any_bloom` | `Interval` |  | P(developing or at the intake). | احتمال التطوّر أو الوجود عند المأخذ. |
| `within` | `Array<HorizonProbability>` |  | P(at_intake within 1, 3 and 7 days). | احتمال بلوغ المأخذ خلال 1 و3 و7 أيام. |
| `staleness_days` | `number \| null` | d | Days since the last clear satellite observation (absent if none yet). | الأيام منذ آخر رصد صافٍ بالقمر الصناعي (يغيب إن لم يوجد بعد). |
| `observation` | `CoverageState` |  | Coverage on this day. | التغطية في هذا اليوم. |
| `alert` | `boolean` |  | Detector alert on this day. | إنذار الكاشف في هذا اليوم. |
| `n_draws` | `number` |  | Posterior parameter draws used. | عدد سحبات المعاملات اللاحقة المستخدمة. |
| `seed` | `number` |  | Seed of the parameter draws. | بذرة سحبات المعاملات. |
| `parameters` | `Array<BeliefParameter>` |  | Parameters used, with posteriors. | المعاملات المستخدمة مع توزيعاتها اللاحقة. |

## Parameter

A model parameter with provenance. The evidence level is required.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `key` | `string` |  | Parameter key. | مفتاح المعامل. |
| `label` | `string` |  | Plain language name. | اسم بلغة بسيطة. |
| `value` | `number` |  | Nominal value. | القيمة الاسمية. |
| `unit` | `string` |  | Unit of the value. | وحدة القيمة. |
| `evidence_level` | `EvidenceLevel` |  | Evidence level of this parameter. | مستوى الأدلة لهذا المعامل. |
| `source` | `ParamSource` |  | Where the value comes from. | مصدر القيمة. |
| `provenance` | `string` |  | Reasoning or citation behind the value. | المنطق أو المرجع وراء القيمة. |
| `rel_spread` | `number` | 1 | Relative spread (one standard deviation on the log scale). | الانتشار النسبي (انحراف معياري واحد على المقياس اللوغاريتمي). |
| `adverse` | `"up" \| "down"` |  | Direction in which the parameter makes outcomes worse. | الاتجاه الذي يجعل فيه المعامل النتائج أسوأ. |

## PlantProfile

A hypothetical plant. Every parameter carries an evidence level and provenance.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `id` | `string` |  | Profile identifier. | معرّف الملف التعريفي. |
| `name` | `string` |  | Profile name. | اسم الملف التعريفي. |
| `hypothetical` | `true` |  | Always true: no real plant is modelled. | صحيح دائمًا: لا تُنمذج أي محطة حقيقية. |
| `description` | `string` |  | What the profile represents. | ما يمثّله الملف التعريفي. |
| `parameters` | `Array<Parameter>` |  | All parameters. | جميع المعاملات. |

## Limits

Hard limits and risk budgets of the decision.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `fouling_limit` | `number` | 1 | Fouling index hard limit. | الحد الصارم لمؤشر الانسداد. |
| `fouling_risk_budget` | `number` | 1 | Largest allowed P(fouling breach) over the horizon. | أكبر احتمال مسموح لتجاوز حد الانسداد خلال الأفق. |
| `water_allowance_m3` | `number` | m3 | Unserved water allowed over the horizon before it counts as a breach. | كمية المياه غير المزوّدة المسموح بها خلال الأفق قبل اعتبارها تجاوزًا. |
| `water_risk_budget` | `number` | 1 | Largest allowed P(unserved water above the allowance). | أكبر احتمال مسموح لتجاوز المياه غير المزوّدة الحد المسموح. |
| `horizon_hours` | `number` | h | Decision horizon. | أفق القرار. |
| `dwell_hours` | `number` | h | Minimum time before a less restrictive change. | أقل مدة قبل التحول إلى إجراء أقل تقييدًا. |

## PlantState

Current state of the hypothetical plant.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `fouling_index` | `number` | 1 | Current fouling index (1 is the hard limit). | مؤشر الانسداد الحالي (1 هو الحد الصارم). |
| `storage_hours` | `number` | h | Product water in storage, in hours of demand. | المياه المنتجة في الخزان بساعات من الطلب. |
| `current_action` | `ActionKind` |  | Action in force. | الإجراء الساري. |
| `current_scale` | `number` | 1 | Flow scale in force. | مقياس التدفق الساري. |
| `hours_in_action` | `number` | h | Hours since the action in force began. | الساعات منذ بدء الإجراء الساري. |

## CandidateEvaluation

Risk of one candidate action over the horizon.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `action` | `ActionKind` |  | Candidate action. | الإجراء المرشّح. |
| `scale` | `number` | 1 | Flow scale q. | مقياس التدفق q. |
| `p_fouling_breach` | `number` | 1 | P(fouling index reaches the limit). | احتمال بلوغ مؤشر الانسداد الحد. |
| `p_water_breach` | `number` | 1 | P(unserved water above the allowance). | احتمال تجاوز المياه غير المزوّدة الحد المسموح. |
| `expected_unserved_m3` | `number` | m3 | Expected unserved water. | المياه غير المزوّدة المتوقعة. |
| `feasible` | `boolean` |  | Both risks within budget. | كلا الخطرين ضمن الميزانية. |

## ConstraintStatus

How close a constraint is to its budget for the chosen action.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `name` | `"fouling" \| "water_security" \| "dwell"` |  | Constraint name. | اسم القيد. |
| `value` | `number` |  | Current value (probability or hours). | القيمة الحالية (احتمال أو ساعات). |
| `budget` | `number` |  | Budget or limit. | الميزانية أو الحد. |
| `used_percent` | `number` | % | Share of the budget used, capped at 100. | نسبة الميزانية المستخدمة، بحد أقصى 100. |

## InspectAssessment

Pre posterior value of a drone survey against its cost.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `value_cu` | `number` | CU | Expected reduction in loss from one survey, in cost units (hypothetical). | الانخفاض المتوقع في الخسارة من مسح واحد بوحدات تكلفة افتراضية. |
| `sortie_cost_cu` | `number` | CU | Cost of one sortie (hypothetical). | تكلفة طلعة واحدة (افتراضية). |
| `break_even_cost_cu` | `number` | CU | Sortie cost at which the survey just pays. | تكلفة الطلعة التي يتعادل عندها المسح. |
| `availability` | `number` | 1 | Probability that weather allows the sortie. | احتمال أن يسمح الطقس بالطلعة. |
| `decision_could_change` | `boolean` |  | Whether some survey outcome changes the best action. | هل يغيّر أي ناتج للمسح الإجراء الأفضل. |
| `inspect` | `boolean` |  | INSPECT advisory set. | تفعيل توصية الفحص. |
| `reasons` | `Array<string>` |  | Reasons in plain language. | الأسباب بلغة بسيطة. |

## Explanation

Structured explanation; the plain language text is rendered from it.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `belief_summary` | `Record<string, number>` |  | Belief quantities used. | كميات الاعتقاد المستخدمة. |
| `plant_state` | `PlantState` |  | Plant state used. | حالة المحطة المستخدمة. |
| `limits` | `Limits` |  | Limits and budgets used. | الحدود والميزانيات المستخدمة. |
| `candidates` | `Array<CandidateEvaluation>` |  | Every candidate with its risks. | كل إجراء مرشّح مع مخاطره. |
| `unconstrained_action` | `ActionKind` |  | Action before the dwell rule. | الإجراء قبل قاعدة مدة البقاء. |
| `unconstrained_scale` | `number` | 1 | Scale before the dwell rule. | المقياس قبل قاعدة مدة البقاء. |
| `dwell_held` | `boolean` |  | Whether the dwell rule held a more restrictive action. | هل أبقت قاعدة مدة البقاء على إجراء أكثر تقييدًا. |
| `binding_constraint` | `string \| null` |  | Constraint that stops a more permissive action. | القيد الذي يمنع إجراءً أكثر تساهلًا. |
| `evidence_level` | `EvidenceLevel` |  | Evidence level of the plant profile. | مستوى أدلة ملف المحطة. |
| `assumption_share` | `number` | 1 | Share of plant parameters that are assumptions. | نسبة معاملات المحطة التي هي افتراضات. |
| `n_samples` | `number` |  | Monte Carlo samples (posterior draws). | عينات مونت كارلو (سحبات لاحقة). |
| `inspect` | `InspectAssessment \| null` |  | Survey value assessment, if computed. | تقييم قيمة المسح إن حُسب. |
| `what_would_change` | `Array<string>` |  | Conditions that would change the advisory. | الظروف التي ستغيّر التوصية. |

## PlainText

Three sentences rendered from the explanation.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `what` | `string` |  | What to do. | ما يجب فعله. |
| `why` | `string` |  | Why. | لماذا. |
| `change` | `string` |  | What would change this. | ما الذي سيغيّر ذلك. |

## Advisory

An advisory for one site and time. It is advice, never a control action.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `id` | `string` |  | Identifier: the inputs hash. | المعرّف: بصمة المدخلات. |
| `site` | `string` |  | Site identifier. | معرّف الموقع. |
| `issued_for` | `string` |  | Time the advisory applies to (UTC). | الوقت الذي تنطبق عليه التوصية (بالتوقيت العالمي). |
| `action` | `ActionKind` |  | Advised action. | الإجراء الموصى به. |
| `scale` | `number` | 1 | Advised flow scale q. | مقياس التدفق الموصى به q. |
| `reasons` | `Array<string>` |  | Reasons in plain language. | الأسباب بلغة بسيطة. |
| `binding_constraint` | `string \| null` |  | Binding constraint. | القيد الحاكم. |
| `p_breach_full_scale` | `number` | 1 | P(fouling limit reached within the horizon at full scale). | احتمال بلوغ حد الانسداد خلال الأفق عند التشغيل الكامل. |
| `time_to_limit_hours` | `number \| null` | h | Hours until the limit at full scale at the 95 percent risk quantile (absent if beyond the horizon). | الساعات حتى بلوغ الحد عند التشغيل الكامل عند مئين الخطر 95 (يغيب إن تجاوز الأفق). |
| `constraints` | `Array<ConstraintStatus>` |  | How close each constraint is. | مدى قرب كل قيد من حدّه. |
| `evidence_level` | `EvidenceLevel` |  | Evidence level of the advisory. | مستوى أدلة التوصية. |
| `assumption_share` | `number` | 1 | Share of plant parameters that are assumptions. | نسبة معاملات المحطة التي هي افتراضات. |
| `inspect` | `boolean` |  | INSPECT advisory (task a survey drone). | توصية الفحص (تكليف طائرة مسح). |
| `inspect_reasons` | `Array<string>` |  | Reasons for or against INSPECT. | أسباب الفحص أو عدمه. |
| `explanation` | `Explanation` |  | Structured explanation (required). | شرح منظّم (إلزامي). |
| `text` | `PlainText` |  | Plain language rendering. | صياغة بلغة بسيطة. |
| `inputs_hash` | `string` |  | SHA-256 of the canonical inputs. | بصمة SHA-256 للمدخلات المعيارية. |
| `seed` | `number` |  | Seed used. | البذرة المستخدمة. |
| `label` | `string` |  | Context label, for example the replay label. | وصف السياق، مثل وصف الإعادة. |

## Scenario

A user bloom scenario for the Scenario Lab (synthetic).

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `site` | `string` |  | Site whose seasonality and coverage are used. | الموقع الذي تُستخدم موسميته وتغطيته. |
| `start_date` | `string` |  | First day. | اليوم الأول. |
| `days` | `number` | d | Scenario length. | طول السيناريو. |
| `onset_day` | `number \| null` | d | Day the bloom enters the watch zone (absent for none). | اليوم الذي يدخل فيه الازدهار منطقة المراقبة (يغيب إن لم يوجد). |
| `days_to_intake` | `number` | d | Days from watch zone to intake. | الأيام من منطقة المراقبة إلى المأخذ. |
| `duration_days` | `number` | d | Days the bloom stays at the intake. | الأيام التي يبقى فيها الازدهار عند المأخذ. |
| `intensity` | `number` | 1 | Bloom load added at the intake, relative to the design load. | حمل الازدهار المضاف عند المأخذ نسبةً إلى حمل التصميم. |
| `detector_availability` | `number` | 1 | Share of days with a clear satellite view. | نسبة الأيام ذات الرؤية الصافية. |
| `detector_visible` | `boolean` |  | Whether the bloom is visible to the broadband detector. | هل الازدهار مرئي للكاشف عريض النطاق. |
| `seed` | `number` |  | Seed. | البذرة. |

## MetricSummary

Mean of a metric over seeds with a 95 percent interval.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `mean` | `number` |  | Mean over seeds. | المتوسط عبر البذور. |
| `lo` | `number` |  | Lower 95 percent bound of the mean. | الحد الأدنى 95 بالمئة للمتوسط. |
| `hi` | `number` |  | Upper 95 percent bound of the mean. | الحد الأعلى 95 بالمئة للمتوسط. |
| `unit` | `string` |  | Unit. | الوحدة. |
| `n` | `number` |  | Number of seeds. | عدد البذور. |

## PolicyResult

Results of one policy on one generator.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `policy` | `string` |  | Policy identifier. | معرّف السياسة. |
| `generator` | `"G1" \| "G2"` |  | Scenario generator. | مولّد السيناريوهات. |
| `n_seeds` | `number` |  | Seeds run. | البذور المنفّذة. |
| `metrics` | `Record<string, MetricSummary>` |  | Every metric, never collapsed. | كل مقياس على حدة دون دمج. |

## Waypoint

A mission waypoint.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `lat` | `number` | deg | Latitude. | خط العرض. |
| `lon` | `number` | deg | Longitude. | خط الطول. |
| `alt_m` | `number` | m | Altitude above the take off point. | الارتفاع فوق نقطة الإقلاع. |

## DroneProfile

Hypothetical survey drone.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `endurance_min` | `number` |  | Endurance. | مدة التحمل. |
| `cruise_speed_ms` | `number` | m/s | Cruise speed. | سرعة الطيران. |
| `reserve_fraction` | `number` | 1 | Battery reserve kept back. | احتياطي البطارية المحفوظ. |
| `wind_limit_ms` | `number` | m/s | Wind speed above which the drone does not fly. | سرعة الرياح التي لا تطير فوقها الطائرة. |
| `altitude_m` | `number` | m | Survey altitude. | ارتفاع المسح. |

## Mission

A survey mission. For simulation and review only.

| Field | Type | Unit | English | العربية |
|---|---|---|---|---|
| `id` | `string` |  | Identifier: the inputs hash. | المعرّف: بصمة المدخلات. |
| `site` | `string` |  | Site identifier. | معرّف الموقع. |
| `radius_m` | `number` | m | Survey radius offshore of the intake. | نصف قطر المسح بعيدًا عن المأخذ. |
| `line_spacing_m` | `number` | m | Spacing of survey lines. | المسافة بين خطوط المسح. |
| `drone` | `DroneProfile` |  | Drone profile. | ملف الطائرة. |
| `waypoints` | `Array<Waypoint>` |  | Waypoints in order, starting and ending at home. | نقاط الطريق بالترتيب، تبدأ وتنتهي عند نقطة الانطلاق. |
| `distance_m` | `number` | m | Total path length. | الطول الكلي للمسار. |
| `flight_time_s` | `number` | s | Flight time at cruise speed. | زمن الطيران بسرعة الطيران. |
| `usable_time_s` | `number` | s | Endurance less reserve. | التحمل بعد خصم الاحتياطي. |
| `feasible` | `boolean` |  | Whether the mission fits the profile. | هل تتسع المهمة ضمن ملف الطائرة. |
| `refused_reason` | `string \| null` |  | Why a mission was refused. | سبب رفض المهمة. |
| `notice` | `"For simulation and review only. Real flights need the operator's own safety case and the regulator's approval."` |  | Simulation only statement (always present). | بيان المحاكاة فقط (موجود دائمًا). |
