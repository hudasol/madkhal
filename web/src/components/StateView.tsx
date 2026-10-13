import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";

export function Loading({ what }: { what?: string }) {
  const { t } = useTranslation();
  return (
    <div className="state" role="status" aria-busy="true" aria-live="polite">
      {t("state.loading")}
      {what ? `: ${what}` : ""}
    </div>
  );
}

export function ErrorView({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const detail = error instanceof ApiError ? `${error.title}. ${error.detail}` : "";
  return (
    <div className="state" role="alert">
      <p>{t("state.error")}</p>
      {detail ? <p className="muted">{detail}</p> : null}
      {onRetry ? (
        <button type="button" className="btn" onClick={onRetry}>
          {t("state.retry")}
        </button>
      ) : null}
    </div>
  );
}

export function Empty() {
  const { t } = useTranslation();
  return (
    <div className="state" role="status">
      {t("state.empty")}
    </div>
  );
}
