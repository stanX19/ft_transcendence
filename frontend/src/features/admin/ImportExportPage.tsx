import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { ApiError, apiRequest } from "../../shared/api";
import { Button, Card, ErrorAlert, FormField, PageHeader, Select } from "../../shared/components";
import { type Translator, useTranslation } from "../../shared/i18n";
import { useAuth } from "../auth";

type CatalogFormat = "csv" | "json" | "xml";

interface ImportIssue {
  record: number | null;
  message: string;
  fields?: string[];
}

interface ImportResult {
  format: CatalogFormat;
  inserted: number;
  updated: number;
  rejected: number;
  errors: ImportIssue[];
  summary?: {
    inserted: number;
    updated: number;
    rejected: number;
  };
}

const formats: Array<{ value: CatalogFormat; label: string; extension: string }> = [
  { value: "csv", label: "CSV", extension: ".csv" },
  { value: "json", label: "JSON", extension: ".json" },
  { value: "xml", label: "XML", extension: ".xml" },
];

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}

function isImportResult(value: unknown): value is ImportResult {
  if (!value || typeof value !== "object") return false;
  const result = value as Partial<ImportResult>;
  return (
    (result.format === "csv" || result.format === "json" || result.format === "xml") &&
    typeof result.inserted === "number" &&
    typeof result.updated === "number" &&
    typeof result.rejected === "number" &&
    Array.isArray(result.errors)
  );
}

function errorMessage(error: unknown, fallback: string, t: Translator): string {
  if (error instanceof ApiError && error.status === 403) {
    return t("data.accessDetail");
  }
  return fallback;
}

export function ImportExportPage() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [format, setFormat] = useState<CatalogFormat>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [exporting, setExporting] = useState<CatalogFormat | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  if (user?.role !== "LIBRARIAN" && user?.role !== "ADMIN") {
    return <PageMessage title={t("data.accessTitle")} detail={t("data.accessDetail")} />;
  }

  async function download(formatToExport: CatalogFormat) {
    setExporting(formatToExport);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`/api/admin/import-export/export?format=${formatToExport}`, { credentials: "include" });
      if (!response.ok) throw new ApiError(response.status, "export_failed", t("data.exportFailed"));
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `libraryos-catalog.${formatToExport}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setMessage(t("data.exportStarted", { format: formatToExport.toUpperCase() }));
    } catch (downloadError) {
      setError(errorMessage(downloadError, t("data.exportFailed"), t));
    } finally {
      setExporting(null);
    }
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setError(null);
    setMessage(null);
    setResult(null);
  }

  async function importCatalog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError(t("data.chooseFile"));
      return;
    }
    setIsImporting(true);
    setError(null);
    setMessage(null);
    setResult(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", format);
    try {
      const imported = await apiRequest<ImportResult>("/api/admin/import-export/import", {
        method: "POST",
        body: formData,
      });
      setResult(imported);
      setMessage(t("data.importCompleted"));
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (importError) {
      if (importError instanceof ApiError && isImportResult(importError.body)) {
        setResult(importError.body);
      }
      setError(errorMessage(importError, t("data.importFailed"), t));
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl">
      <PageHeader description={t("data.description")} eyebrow={t("data.eyebrow")} title={t("data.title")} />

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card className="p-6" aria-labelledby="export-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="export-heading">{t("data.exportTitle")}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{t("data.exportDescription")}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            {formats.map((item) => (
              <Button disabled={exporting !== null} key={item.value} loading={exporting === item.value} onClick={() => void download(item.value)} type="button" variant="secondary">
                {exporting === item.value ? t("data.exportPreparing") : t("data.exportAction", { format: item.label })}
              </Button>
            ))}
          </div>
        </Card>

        <Card className="p-6" aria-labelledby="import-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="import-heading">{t("data.importTitle")}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{t("data.importDescription")}</p>
          <form className="mt-5 space-y-4" onSubmit={importCatalog}>
            <FormField htmlFor="catalog-format" label={t("data.fileFormat")}>
              <Select id="catalog-format" onChange={(event) => setFormat(event.target.value as CatalogFormat)} value={format}>
                {formats.map((item) => <option key={item.value} value={item.value}>{item.label} ({item.extension})</option>)}
              </Select>
            </FormField>
            <FormField htmlFor="catalog-file" label={t("data.catalogFile")}>
              <input accept=".csv,.json,.xml,text/csv,application/json,application/xml" className="mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:font-medium" id="catalog-file" onChange={chooseFile} ref={inputRef} type="file" />
            </FormField>
            {file ? <p className="text-sm text-slate-600">{t("data.selectedFile")} <span className="font-medium text-slate-900">{file.name}</span></p> : null}
            <Button disabled={isImporting || exporting !== null} loading={isImporting} type="submit">
              {isImporting ? t("data.validateImport") : t("data.importAction")}
            </Button>
          </form>
        </Card>
      </div>

      {message ? <p className="mt-6 text-sm text-emerald-700" role="status">{message}</p> : null}
      {error ? <ErrorAlert className="mt-3" message={error} /> : null}
      {result ? (
        <Card className="mt-6 p-6" aria-labelledby="import-result-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="import-result-heading">{t("data.resultTitle")}</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">{t("data.inserted")}</dt><dd className="mt-1 text-2xl font-semibold text-emerald-700">{result.inserted}</dd></div>
            <div><dt className="text-slate-500">{t("data.updated")}</dt><dd className="mt-1 text-2xl font-semibold text-sky-700">{result.updated}</dd></div>
            <div><dt className="text-slate-500">{t("data.rejected")}</dt><dd className="mt-1 text-2xl font-semibold text-rose-700">{result.rejected}</dd></div>
          </dl>
          {result.errors.length > 0 ? (
            <div className="mt-5 rounded-xl bg-rose-50 p-4" role="alert">
              <h3 className="font-medium text-rose-900">{t("data.reviewRecords")}</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-rose-800">
                {result.errors.map((issue, index) => <li key={`${issue.record ?? "document"}-${index}`}>{issue.record ? t("data.record", { number: issue.record }) : t("data.document")}{issue.message}</li>)}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}
    </section>
  );
}
