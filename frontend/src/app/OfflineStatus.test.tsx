import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../shared/i18n";
import { OfflineStatus } from "./OfflineStatus";

let online = true;

function setBrowserOnline(value: boolean) {
  online = value;
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    get: () => online,
  });
}

describe("OfflineStatus", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setBrowserOnline(true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows translated offline and reconnecting states", () => {
    setBrowserOnline(false);
    render(
      <I18nProvider>
        <OfflineStatus />
      </I18nProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/you.?re offline/i);

    act(() => {
      setBrowserOnline(true);
      window.dispatchEvent(new Event("online"));
    });
    expect(screen.getByRole("status")).toHaveTextContent(/connection restored/i);

    act(() => {
      vi.advanceTimersByTime(3_000);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
