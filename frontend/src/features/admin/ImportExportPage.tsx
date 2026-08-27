import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

import { ApiError, apiRequest } from "../../shared/api";
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

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 403) {
    return "Only librarians and administrators can manage catalog data.";
  }
  return fallback;
}

export function ImportExportPage() {
  const { user } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [format, setFormat] = useState<CatalogFormat>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [exporting, setExporting] = useState<CatalogFormat | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  if (user?.role !== "LIBRARIAN" && user?.role !== "ADMIN") {
    return <PageMessage title="Catalog data access required" detail="Only librarians and administrators can import or export catalog records." />;
  }

  async function download(formatToExport: CatalogFormat) {
    setExporting(formatToExport);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`/api/admin/import-export/export?format=${formatToExport}`, { credentials: "include" });
      if (!response.ok) throw new ApiError(response.status, "export_failed", "The catalog could not be exported.");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `libraryos-catalog.${formatToExport}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setMessage(`${formatToExport.toUpperCase()} catalog export started.`);
    } catch (downloadError) {
      setError(errorMessage(downloadError, "We could not export the catalog. Please try again."));
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
      setError("Choose a CSV, JSON, or XML catalog file first.");
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
      setMessage("Catalog import completed.");
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (importError) {
      if (importError instanceof ApiError && isImportResult(importError.body)) {
        setResult(importError.body);
      }
      setError(errorMessage(importError, "The catalog import was not applied. Review the reported records."));
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Catalog data</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Import &amp; export</h1>
        <p className="mt-3 max-w-2xl text-slate-600">Move catalog records in a familiar format. Imports are validated completely before any record is changed.</p>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="export-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="export-heading">Export catalog</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Download the current catalog for a spreadsheet, integration, or archive.</p>
          <div className="mt-5 flex flex-wrap gap-3">
            {formats.map((item) => (
              <button className="rounded-xl border border-slate-300 px-4 py-2.5 font-medium text-slate-700 hover:border-sky-400 hover:text-sky-800 disabled:cursor-not-allowed disabled:opacity-50" disabled={exporting !== null} key={item.value} onClick={() => void download(item.value)} type="button">
                {exporting === item.value ? "Preparing…" : `Export ${item.label}`}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="import-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="import-heading">Import catalog</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Upload a complete CSV, JSON, or XML document. Existing records match by id, ISBN, or slug.</p>
          <form className="mt-5 space-y-4" onSubmit={importCatalog}>
            <label className="block text-sm font-medium text-slate-800" htmlFor="catalog-format">
              File format
              <select className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" id="catalog-format" onChange={(event) => setFormat(event.target.value as CatalogFormat)} value={format}>
                {formats.map((item) => <option key={item.value} value={item.value}>{item.label} ({item.extension})</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium text-slate-800" htmlFor="catalog-file">
              Catalog file
              <input accept=".csv,.json,.xml,text/csv,application/json,application/xml" className="mt-2 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:font-medium" id="catalog-file" onChange={chooseFile} ref={inputRef} type="file" />
            </label>
            {file ? <p className="text-sm text-slate-600">Selected: <span className="font-medium text-slate-900">{file.name}</span></p> : null}
            <button className="rounded-xl bg-slate-950 px-4 py-2.5 font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50" disabled={isImporting || exporting !== null} type="submit">
              {isImporting ? "Validating & importing…" : "Import catalog"}
            </button>
          </form>
        </section>
      </div>

      {message ? <p className="mt-6 text-sm text-emerald-700" role="status">{message}</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-700" role="alert">{error}</p> : null}
      {result ? (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="import-result-heading">
          <h2 className="text-lg font-semibold text-slate-950" id="import-result-heading">Import result</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
            <div><dt className="text-slate-500">Inserted</dt><dd className="mt-1 text-2xl font-semibold text-emerald-700">{result.inserted}</dd></div>
            <div><dt className="text-slate-500">Updated</dt><dd className="mt-1 text-2xl font-semibold text-sky-700">{result.updated}</dd></div>
            <div><dt className="text-slate-500">Rejected</dt><dd className="mt-1 text-2xl font-semibold text-rose-700">{result.rejected}</dd></div>
          </dl>
          {result.errors.length > 0 ? (
            <div className="mt-5 rounded-xl bg-rose-50 p-4" role="alert">
              <h3 className="font-medium text-rose-900">Review these records</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-rose-800">
                {result.errors.map((issue, index) => <li key={`${issue.record ?? "document"}-${index}`}>{issue.record ? `Record ${issue.record}: ` : "Document: "}{issue.message}</li>)}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
