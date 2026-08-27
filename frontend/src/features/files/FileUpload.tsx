import { useRef, useState, type ChangeEvent } from "react";

import { ApiError } from "../../shared/api";
import { Button, ErrorAlert } from "../../shared/components";
import { useTranslation } from "../../shared/i18n";

export interface UploadedFile {
  id: number;
  owner_user_id: number | null;
  book_id: number | null;
  kind: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  url: string;
}

interface FileUploadProps {
  endpoint: string;
  accept: string;
  label: string;
  helper: string;
  fields?: Record<string, string>;
  onUploaded: (file: UploadedFile) => void;
}

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function parseError(xhr: XMLHttpRequest): ApiError {
  let body: { error?: { code?: string; message?: string } } = {};
  try {
    body = JSON.parse(xhr.responseText) as typeof body;
  } catch {
    // Keep one safe message when the server did not return JSON.
  }
  return new ApiError(
    xhr.status,
    body.error?.code ?? "request_failed",
    body.error?.message ?? "The upload could not be completed.",
  );
}

function sendFile(
  endpoint: string,
  file: File,
  fields: Record<string, string> | undefined,
  onProgress: (progress: number) => void,
): Promise<UploadedFile> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    Object.entries(fields ?? {}).forEach(([name, value]) => formData.append(name, value));
    xhr.open("POST", endpoint);
    xhr.withCredentials = true;
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const payload = JSON.parse(xhr.responseText) as { file?: UploadedFile };
          if (payload.file) {
            resolve(payload.file);
            return;
          }
        } catch {
          // Fall through to the same safe upload error.
        }
      }
      reject(parseError(xhr));
    });
    xhr.addEventListener("error", () => reject(new Error("The upload could not be sent.")));
    xhr.addEventListener("abort", () => reject(new Error("The upload was cancelled.")));
    xhr.send(formData);
  });
}

export function FileUpload({
  endpoint,
  accept,
  label,
  helper,
  fields,
  onUploaded,
}: FileUploadProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setError(null);
    setSelectedFile(nextFile);
    if (nextFile && nextFile.size > MAX_UPLOAD_BYTES) {
      setError(t("file.tooLarge"));
    }
  }

  async function upload() {
    if (!selectedFile || selectedFile.size > MAX_UPLOAD_BYTES) return;
    setError(null);
    setProgress(0);
    setIsUploading(true);
    try {
      const uploaded = await sendFile(endpoint, selectedFile, fields, setProgress);
      onUploaded(uploaded);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setProgress(100);
    } catch (uploadError) {
      setError(
        uploadError instanceof ApiError && uploadError.status === 422
          ? t("file.invalid")
          : t("file.genericError"),
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-dashed border-sky-200 bg-sky-50/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="mt-1 text-xs text-slate-500">{helper}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            accept={accept}
            className="max-w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-2 file:font-medium file:text-sky-800"
            disabled={isUploading}
            onChange={selectFile}
            ref={inputRef}
            type="file"
          />
          <Button
            disabled={!selectedFile || Boolean(error) || isUploading}
            loading={isUploading}
            onClick={() => void upload()}
            size="sm"
            type="button"
          >
            {isUploading ? t("file.uploading") : t("file.upload")}
          </Button>
        </div>
      </div>
      {isUploading || progress === 100 ? (
        <div className="mt-3" aria-live="polite">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>{isUploading ? t("file.uploadingFile") : t("file.uploadComplete")}</span>
            <span>{progress}%</span>
          </div>
          <progress aria-label={t("file.progress")} className="mt-1 h-2 w-full accent-sky-700" max={100} value={progress} />
        </div>
      ) : null}
      {error ? <ErrorAlert className="mt-3" message={error} /> : null}
    </div>
  );
}
