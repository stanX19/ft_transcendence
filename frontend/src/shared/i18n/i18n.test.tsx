import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { I18nProvider, LanguageSwitcher, localeMessages, useTranslation } from ".";

function TranslationProbe() {
  const { locale, t } = useTranslation();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="books">{t("nav.books")}</span>
      <span data-testid="pagination">{t("catalog.pageSummary", { page: 2, totalPages: 3, count: 5 })}</span>
      <LanguageSwitcher />
    </div>
  );
}

describe("LibraryOS internationalization", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = "";
  });

  it("switches the active locale and updates translated content", async () => {
    render(
      <I18nProvider>
        <TranslationProbe />
      </I18nProvider>,
    );

    expect(screen.getByTestId("locale")).toHaveTextContent("en");
    expect(screen.getByTestId("books")).toHaveTextContent("Books");
    expect(screen.getByTestId("pagination")).toHaveTextContent("Page 2 of 3 · 5 books");

    fireEvent.change(screen.getByRole("combobox", { name: /language/i }), { target: { value: "ms" } });
    await waitFor(() => expect(screen.getByTestId("locale")).toHaveTextContent("ms"));
    expect(screen.getByTestId("books")).toHaveTextContent("Buku");
    expect(document.documentElement.lang).toBe("ms");

    fireEvent.change(screen.getByRole("combobox", { name: /bahasa|language/i }), { target: { value: "zh" } });
    await waitFor(() => expect(screen.getByTestId("locale")).toHaveTextContent("zh"));
    expect(screen.getByTestId("books")).toHaveTextContent("书籍");
  });

  it("keeps all locale dictionaries aligned", () => {
    const keys = Object.keys(localeMessages.en).sort();
    expect(Object.keys(localeMessages.ms).sort()).toEqual(keys);
    expect(Object.keys(localeMessages.zh).sort()).toEqual(keys);
    expect(keys.length).toBeGreaterThan(80);
  });
});
