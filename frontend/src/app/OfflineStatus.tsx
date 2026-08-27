import { useEffect, useState } from "react";
import { Wifi, WifiOff } from "lucide-react";

import { useTranslation } from "../shared/i18n";

const RECONNECTED_NOTICE_MS = 3_000;

function readOnlineState(): boolean {
  return typeof navigator === "undefined" || navigator.onLine;
}

export function OfflineStatus() {
  const { t } = useTranslation();
  const [isOnline, setIsOnline] = useState(readOnlineState);
  const [showReconnected, setShowReconnected] = useState(false);

  useEffect(() => {
    let reconnectTimer: number | undefined;

    function handleOffline() {
      setIsOnline(false);
      setShowReconnected(false);
    }

    function handleOnline() {
      setIsOnline(true);
      setShowReconnected(true);
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      reconnectTimer = window.setTimeout(() => setShowReconnected(false), RECONNECTED_NOTICE_MS);
    }

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    };
  }, []);

  if (isOnline && !showReconnected) return null;

  return (
    <div
      aria-live="polite"
      className={isOnline
        ? "flex items-center justify-center gap-2 bg-emerald-50 px-4 py-2 text-sm text-emerald-900"
        : "flex items-center justify-center gap-2 bg-amber-50 px-4 py-2 text-sm text-amber-950"}
      role="status"
    >
      {isOnline ? <Wifi aria-hidden="true" size={16} /> : <WifiOff aria-hidden="true" size={16} />}
      <span>{isOnline ? t("offline.reconnected") : t("offline.message")}</span>
    </div>
  );
}
