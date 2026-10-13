import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { MODE } from "../api/client";
import { usePreset, useScenario } from "../api/hooks";
import type { ScenarioResponse } from "../api/types";
import { AdvisoryPanel } from "../components/Advisory";
import { BandChart } from "../components/BandChart";
import { Ribbon } from "../components/Ribbon";
import { ErrorView, Loading } from "../components/StateView";
import { formatNumber } from "../format";
import { useSettings } from "../settings";

const DAYS = 30;
const PRESETS = ["visible_bloom", "invisible_bloom", "blind_season", "quiet"] as const;

/** A timeline strip with a draggable bloom marker; the arrow keys move it too. */
function OnsetPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const ref = useRef<SVGSVGElement | null>(null);
  const rtl = s.lang === "ar";
  const W = 600;
  const x = (d: number) => {
    const v = 10 + (d / (DAYS - 1)) * (W - 20);
    return rtl ? W - v : v;
  };
  const fromClient = (cx: number) => {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return value ?? 0;
    let f = (cx - r.left) / r.width;
    if (rtl) f = 1 - f;
    return Math.max(0, Math.min(DAYS - 1, Math.round(((f * W - 10) / (W - 20)) * (DAYS - 1))));
  };
  const v = value ?? 0;
  return (
    <div className="stack">
      <svg
        ref={ref}
        viewBox={`0 0 ${W} 50`}
        className="onset-picker"
        onPointerDown={(e) => {
          (e.target as Element).setPointerCapture?.(e.pointerId);
          onChange(fromClient(e.clientX));
        }}
        onPointerMove={(e) => {
          if (e.buttons === 1) onChange(fromClient(e.clientX));
        }}
        aria-hidden="true"
      >
        <rect x="10" y="22" width={W - 20} height="6" fill="var(--clear)" />
        {Array.from({ length: DAYS }, (_, d) => (
          <line
            key={d}
            x1={x(d)}
            x2={x(d)}
            y1="18"
            y2="32"
            stroke="var(--border)"
            strokeOpacity="0.4"
          />
        ))}
        {value !== null ? (
          <polygon
            points={`${x(v)},10 ${x(v) + 9},40 ${x(v) - 9},40`}
            fill="var(--park)"
            stroke="var(--ink)"
            strokeWidth="2"
          />
        ) : null}
      </svg>
      <label className="row">
        <span>{t("lab.onset")}</span>
        <input
          type="range"
          min={-1}
          max={DAYS - 1}
          value={value ?? -1}
          aria-valuetext={value === null ? t("lab.noBloom") : String(value)}
          onChange={(e) => {
            const n = Number(e.target.value);
            onChange(n < 0 ? null : n);
          }}
        />
        <span className="num">{value === null ? t("lab.noBloom") : formatNumber(value, s)}</span>
      </label>
      <p className="muted">{t("lab.onsetHelp")}</p>
    </div>
  );
}

function Result({ data }: { data: ScenarioResponse }) {
  const { t } = useTranslation();
  const s = useSettings();
  const days = data.days;
  const dates = days.map((d) => d.date);
  const band = {
    lo: days.map((d) => d.within_3[0]!),
    median: days.map((d) => d.within_3[1]!),
    hi: days.map((d) => d.within_3[2]!),
  };
  return (
    <div className="stack">
      <p className="badge warn" lang="en" dir="ltr">
        {data.label}
      </p>
      <Ribbon
        title={t("lab.advice")}
        description={t("timeline.ribbonDesc")}
        dates={dates}
        actions={days.map((d) => d.action)}
        scales={days.map((d) => d.scale)}
      />
      <div className="table-wrap" tabIndex={0}>
        <table>
          <caption className="muted">{t("lab.truth")}</caption>
          <tbody>
            <tr>
              {days.map((d, i) => (
                <td key={d.date} className={`truth ${d.truth}`} title={d.date}>
                  {i % 5 === 0 ? formatNumber(i, s) : ""}
                  <span className="sr-only">{t(`lab.states.${d.truth}`)}</span>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      <BandChart
        title={t("timeline.band")}
        description={t("console.chartDesc")}
        dates={dates}
        band={band}
        clear={days.map((d) => d.clear)}
        alert={days.map((d) => d.alert)}
      />
      <section className="stack" aria-labelledby="plant-h">
        <h3 id="plant-h">{t("lab.plant")}</h3>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <caption className="muted">{t("lab.plant")}</caption>
            <thead>
              <tr>
                <th scope="col">{t("common.date")}</th>
                <th scope="col">{t("lab.truth")}</th>
                <th scope="col">{t("lab.advice")}</th>
                <th scope="col">{t("lab.fouling")}</th>
                <th scope="col">{t("lab.storage")}</th>
                <th scope="col">{t("lab.unservedCol")}</th>
              </tr>
            </thead>
            <tbody>
              {days.map((d) => (
                <tr key={d.date}>
                  <td className="num">{d.date}</td>
                  <td>{t(`lab.states.${d.truth}`)}</td>
                  <td>
                    {d.action === "DERATE"
                      ? `${t("action.DERATE")} ${formatNumber(d.scale, s, 1)}`
                      : t(`action.${d.action}`)}
                  </td>
                  <td className="num">{formatNumber(d.fouling_index, s, 2)}</td>
                  <td className="num">{formatNumber(d.storage_hours, s, 1)}</td>
                  <td className="num">{formatNumber(d.unserved_m3, s)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="num">
          {t("lab.totals", {
            unserved: formatNumber(data.totals.unserved_m3, s),
            shutdowns: formatNumber(data.totals.forced_shutdowns, s),
            cleanings: formatNumber(data.totals.cleanings, s),
          })}
        </p>
      </section>
      <section className="stack" aria-labelledby="ex-h">
        <h3 id="ex-h">{t("lab.explanation")}</h3>
        <AdvisoryPanel adv={data.last_advisory} />
      </section>
    </div>
  );
}

export function LabScreen() {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<(typeof PRESETS)[number]>("visible_bloom");
  const [onset, setOnset] = useState<number | null>(5);
  const [intensity, setIntensity] = useState(1.5);
  const [toIntake, setToIntake] = useState(4);
  const [duration, setDuration] = useState(10);
  const [availability, setAvailability] = useState(0.6);
  const [visible, setVisible] = useState(true);
  const pre = usePreset(preset, MODE === "static");
  const run = useScenario();
  const live = MODE === "live";
  return (
    <div className="stack">
      <h1>{t("lab.title")}</h1>
      <p>{t("lab.intro")}</p>
      {live ? (
        <section className="card stack" aria-label={t("lab.title")}>
          <OnsetPicker value={onset} onChange={setOnset} />
          <div className="grid two">
            <label className="row">
              <span>{t("lab.intensity")}</span>
              <input
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={intensity}
                onChange={(e) => setIntensity(Number(e.target.value))}
              />
            </label>
            <label className="row">
              <span>{t("lab.toIntake")}</span>
              <input
                type="number"
                min={0}
                max={30}
                value={toIntake}
                onChange={(e) => setToIntake(Number(e.target.value))}
              />
            </label>
            <label className="row">
              <span>{t("lab.duration")}</span>
              <input
                type="number"
                min={1}
                max={60}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </label>
            <label className="row">
              <span>{t("lab.availability")}</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={availability}
                onChange={(e) => setAvailability(Number(e.target.value))}
              />
              <span className="num">{Math.round(availability * 100)}%</span>
            </label>
            <label className="row">
              <input
                type="checkbox"
                checked={visible}
                onChange={(e) => setVisible(e.target.checked)}
              />
              <span>{t("lab.visible")}</span>
            </label>
          </div>
          <button
            type="button"
            className="btn"
            disabled={run.isPending}
            onClick={() =>
              run.mutate({
                site: "kalba",
                start_date: "2021-08-20",
                days: DAYS,
                onset_day: onset,
                days_to_intake: toIntake,
                duration_days: duration,
                intensity,
                detector_availability: availability,
                detector_visible: visible,
                seed: 7,
              })
            }
          >
            {run.isPending ? t("lab.running") : t("lab.run")}
          </button>
          {run.isError ? <ErrorView error={run.error} /> : null}
          {run.data ? <Result data={run.data} /> : null}
        </section>
      ) : (
        <section className="card stack" aria-label={t("lab.title")}>
          <p className="state" role="status">
            {t("lab.staticNote")}
          </p>
          <label className="row">
            <span>{t("lab.preset")}</span>
            <select
              value={preset}
              onChange={(e) => setPreset(e.target.value as (typeof PRESETS)[number])}
            >
              {PRESETS.map((p) => (
                <option key={p} value={p}>
                  {t(`lab.presets.${p}`)}
                </option>
              ))}
            </select>
          </label>
          {pre.isLoading ? (
            <Loading />
          ) : pre.isError || !pre.data ? (
            <ErrorView error={pre.error} onRetry={() => void pre.refetch()} />
          ) : (
            <Result data={pre.data} />
          )}
        </section>
      )}
    </div>
  );
}
