import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  FormField,
  Input,
  LinkButton,
  LoadingState,
  Notice,
  PageHeader,
  Select,
  TextArea,
} from "../../shared/components";
import { type Translator, useTranslation } from "../../shared/i18n";
import { FileUpload, type UploadedFile } from "../files";
import { useAuth } from "../auth";

export interface Book {
  id: number;
  isbn: string | null;
  slug: string;
  title: string;
  author: string;
  description: string;
  category: string;
  publication_year: number | null;
  total_copies: number;
  available_copies: number;
  created_at: string;
  updated_at: string;
}

interface BookListResponse {
  items: Book[];
  page: number;
  page_size: number;
  total: number;
}

interface BookResponse {
  book?: Book;
}

interface BookFormValues {
  isbn: string;
  slug: string;
  title: string;
  author: string;
  description: string;
  category: string;
  publication_year: string;
  total_copies: string;
}

function canManageBooks(role: string | undefined): boolean {
  return role === "LIBRARIAN" || role === "ADMIN";
}

function formatAvailability(book: Book, t: Translator): string {
  return t("catalog.availability", { available: book.available_copies, total: book.total_copies });
}

function errorMessage(error: unknown, fallback: string, t: Translator): string {
  if (error instanceof ApiError && error.status === 409) {
    return t("catalog.changeConflict");
  }
  return fallback;
}

function emptyForm(book?: Book): BookFormValues {
  return {
    isbn: book?.isbn ?? "",
    slug: book?.slug ?? "",
    title: book?.title ?? "",
    author: book?.author ?? "",
    description: book?.description ?? "",
    category: book?.category ?? "",
    publication_year: book?.publication_year?.toString() ?? "",
    total_copies: book?.total_copies.toString() ?? "1",
  };
}

function BookForm({
  book,
  onSaved,
  onCancel,
}: {
  book?: Book;
  onSaved: (saved: Book) => void;
  onCancel?: () => void;
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState(() => emptyForm(book));
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setValues(emptyForm(book));
  }, [book]);

  function update(name: keyof BookFormValues, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.reportValidity();
      return;
    }
    setError(null);
    setIsSaving(true);
    const payload = {
      isbn: values.isbn.trim() || null,
      slug: values.slug.trim() || null,
      title: values.title.trim(),
      author: values.author.trim(),
      description: values.description.trim(),
      category: values.category.trim(),
      publication_year: values.publication_year ? Number(values.publication_year) : null,
      total_copies: Number(values.total_copies),
    };
    try {
      const response = await apiRequest<BookResponse>(
        book ? `/api/books/${book.id}` : "/api/books",
        {
          method: book ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        },
      );
      if (!response.book) {
        throw new Error("The catalog response was incomplete.");
      }
      onSaved(response.book);
    } catch (saveError) {
      setError(errorMessage(saveError, t("catalog.saveFailed"), t));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="mt-6 space-y-4 rounded-panel border border-accent-100 bg-accent-50/70 p-5 shadow-panel" onSubmit={submit}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-ink">{book ? t("catalog.editTitle") : t("catalog.addTitle")}</h2>
        {onCancel ? (
          <Button onClick={onCancel} size="sm" variant="ghost" type="button">
            {t("catalog.cancel")}
          </Button>
        ) : null}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField htmlFor="book-title" label={t("catalog.titleField")}>
          <Input id="book-title" minLength={1} onChange={(event) => update("title", event.target.value)} required value={values.title} />
        </FormField>
        <FormField htmlFor="book-author" label={t("catalog.authorField")}>
          <Input id="book-author" minLength={1} onChange={(event) => update("author", event.target.value)} required value={values.author} />
        </FormField>
        <FormField htmlFor="book-category" label={t("catalog.categoryField")}>
          <Input id="book-category" minLength={1} onChange={(event) => update("category", event.target.value)} required value={values.category} />
        </FormField>
        <FormField htmlFor="book-isbn" label={<>{t("catalog.isbnField")} <span className="font-normal text-muted">{t("catalog.optional")}</span></>}>
          <Input id="book-isbn" onChange={(event) => update("isbn", event.target.value)} value={values.isbn} />
        </FormField>
        <FormField htmlFor="book-publication-year" label={<>{t("catalog.publicationYear")} <span className="font-normal text-muted">{t("catalog.optional")}</span></>}>
          <Input id="book-publication-year" max={3000} min={0} onChange={(event) => update("publication_year", event.target.value)} type="number" value={values.publication_year} />
        </FormField>
        <FormField htmlFor="book-total-copies" label={t("catalog.totalCopies")}>
          <Input id="book-total-copies" min={0} onChange={(event) => update("total_copies", event.target.value)} required type="number" value={values.total_copies} />
        </FormField>
      </div>
      <FormField htmlFor="book-description" label={t("catalog.descriptionField")}>
        <TextArea id="book-description" minLength={1} onChange={(event) => update("description", event.target.value)} required value={values.description} />
      </FormField>
      {error ? <ErrorAlert message={error} /> : null}
      <Button disabled={isSaving} loading={isSaving} type="submit">
        {isSaving ? t("catalog.saving") : book ? t("catalog.saveChanges") : t("catalog.addBook")}
      </Button>
    </form>
  );
}

function BookCard({ book }: { book: Book }) {
  const { t } = useTranslation();

  return (
    <Link className="block transition hover:-translate-y-0.5" to={`/books/${book.id}`}>
      <Card className="h-full p-5 transition hover:border-accent-100">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-accent-700">{book.category}</p>
            <h2 className="mt-2 text-lg font-semibold text-ink">{book.title}</h2>
            <p className="mt-1 text-sm text-muted">{book.author}</p>
          </div>
          <Badge variant={book.available_copies > 0 ? "success" : "neutral"}>
            {book.available_copies > 0 ? t("catalog.statusAvailable") : t("catalog.statusCheckedOut")}
          </Badge>
        </div>
        <p className="mt-4 line-clamp-2 text-sm leading-6 text-muted">{book.description}</p>
        <p className="mt-4 text-sm font-medium text-ink-soft">{formatAvailability(book, t)}</p>
      </Card>
    </Link>
  );
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return <EmptyState detail={detail} title={title} />;
}

export function BooksPage() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState({ q: "", author: "", category: "", available: "all", sort: "title", page: 1 });
  const [showCreate, setShowCreate] = useState(false);

  const booksQuery = useQuery({
    queryKey: ["books", filters],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(filters.page), page_size: "20", sort: filters.sort });
      if (filters.q) params.set("q", filters.q);
      if (filters.author) params.set("author", filters.author);
      if (filters.category) params.set("category", filters.category);
      if (filters.available !== "all") params.set("available", filters.available);
      return apiRequest<BookListResponse>(`/api/books?${params.toString()}`);
    },
    refetchInterval: 30_000,
    retry: false,
  });
  const totalPages = Math.max(1, Math.ceil((booksQuery.data?.total ?? 0) / (booksQuery.data?.page_size ?? 20)));

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters((current) => ({ ...current, q: searchInput.trim(), page: 1 }));
  }

  function updateFilter(name: "author" | "category" | "available" | "sort", value: string) {
    setFilters((current) => ({ ...current, [name]: value, page: 1 }));
  }

  function pageChange(nextPage: number) {
    setFilters((current) => ({ ...current, page: nextPage }));
  }

  return (
    <section className="mx-auto max-w-6xl">
      <PageHeader
        actions={canManageBooks(user?.role) ? <Button onClick={() => setShowCreate((current) => !current)}>{showCreate ? t("catalog.cancel") : t("catalog.addBook")}</Button> : null}
        description={t("catalog.description")}
        eyebrow={t("catalog.eyebrow")}
        title={t("catalog.title")}
      />

      {showCreate ? (
        <BookForm
          onCancel={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            void queryClient.invalidateQueries({ queryKey: ["books"] });
          }}
        />
      ) : null}

      <Card className="mt-8 p-4">
        <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" onSubmit={search}>
        <FormField className="lg:col-span-2" htmlFor="catalog-search" label={t("catalog.searchLabel")}>
          <Input id="catalog-search" onChange={(event) => setSearchInput(event.target.value)} placeholder={t("catalog.searchPlaceholder")} value={searchInput} />
        </FormField>
        <FormField htmlFor="catalog-author" label={t("catalog.authorLabel")}>
          <Input id="catalog-author" onChange={(event) => updateFilter("author", event.target.value)} placeholder={t("catalog.authorPlaceholder")} value={filters.author} />
        </FormField>
        <FormField htmlFor="catalog-category" label={t("catalog.categoryLabel")}>
          <Input id="catalog-category" onChange={(event) => updateFilter("category", event.target.value)} placeholder={t("catalog.categoryPlaceholder")} value={filters.category} />
        </FormField>
        <FormField htmlFor="catalog-availability" label={t("catalog.availabilityLabel")}>
          <Select id="catalog-availability" onChange={(event) => updateFilter("available", event.target.value)} value={filters.available}>
            <option value="all">{t("catalog.allBooks")}</option>
            <option value="true">{t("catalog.availableNow")}</option>
            <option value="false">{t("catalog.checkedOut")}</option>
          </Select>
        </FormField>
        <FormField htmlFor="catalog-sort" label={t("catalog.sortLabel")}>
          <Select id="catalog-sort" onChange={(event) => updateFilter("sort", event.target.value)} value={filters.sort}>
            <option value="title">{t("catalog.sortTitle")}</option>
            <option value="author">{t("catalog.sortAuthor")}</option>
            <option value="newest">{t("catalog.sortNewest")}</option>
          </Select>
        </FormField>
        <Button className="sm:col-span-2 lg:col-span-5 lg:justify-self-end" type="submit" variant="accent">{t("catalog.search")}</Button>
        </form>
      </Card>

      {booksQuery.isLoading ? <LoadingState detail={t("catalog.loadingDetail")} title={t("catalog.loadingTitle")} /> : null}
      {booksQuery.error ? <ErrorAlert className="mt-8" message={<><strong>{t("catalog.unavailableTitle")}</strong> {t("catalog.unavailableDetail")}</>} /> : null}
      {booksQuery.data && booksQuery.data.items.length === 0 ? <PageMessage title={t("catalog.noBooksTitle")} detail={t("catalog.noBooksDetail")} /> : null}
      {booksQuery.data && booksQuery.data.items.length > 0 ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {booksQuery.data.items.map((book) => <BookCard book={book} key={book.id} />)}
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 text-sm text-muted">
            <span>{t("catalog.pageSummary", { page: booksQuery.data.page, totalPages, count: booksQuery.data.total })}</span>
            <div className="flex gap-2">
              <Button disabled={filters.page <= 1} onClick={() => pageChange(filters.page - 1)} size="sm" variant="secondary" type="button">{t("catalog.previous")}</Button>
              <Button disabled={filters.page >= totalPages} onClick={() => pageChange(filters.page + 1)} size="sm" variant="secondary" type="button">{t("catalog.next")}</Button>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}

export function BookDetailPage() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [borrowError, setBorrowError] = useState<string | null>(null);
  const [borrowMessage, setBorrowMessage] = useState<string | null>(null);
  const [isBorrowing, setIsBorrowing] = useState(false);
  const [assets, setAssets] = useState<UploadedFile[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const bookQuery = useQuery({
    queryKey: ["books", bookId],
    queryFn: () => apiRequest<BookResponse>(`/api/books/${bookId}`),
    enabled: Boolean(bookId),
    refetchInterval: 30_000,
    retry: false,
  });
  const book = bookQuery.data?.book;

  if (bookQuery.isLoading) return <LoadingState detail={t("book.loadingDetail")} title={t("book.loadingTitle")} />;
  if (bookQuery.error) {
    const notFound = bookQuery.error instanceof ApiError && bookQuery.error.status === 404;
    return <PageMessage title={notFound ? t("book.notFoundTitle") : t("book.unavailableTitle")} detail={notFound ? t("book.notFoundDetail") : t("book.unavailableDetail")} />;
  }
  if (!book) return <PageMessage title={t("book.unavailableTitle")} detail={t("book.noDataDetail")} />;

  async function borrowBook() {
    setBorrowError(null);
    setBorrowMessage(null);
    setIsBorrowing(true);
    try {
      await apiRequest(`/api/books/${book.id}/borrow`, { method: "POST" });
      setBorrowMessage(t("book.loanRecorded"));
      await queryClient.invalidateQueries({ queryKey: ["books"] });
      await queryClient.invalidateQueries({ queryKey: ["loans", "me"] });
    } catch (error) {
      setBorrowError(
        error instanceof ApiError && error.status === 409
          ? t("book.borrowConflict")
          : t("book.borrowFailed"),
      );
    } finally {
      setIsBorrowing(false);
    }
  }

  async function removeBook() {
    setDeleteError(null);
    try {
      await apiRequest(`/api/books/${book.id}`, { method: "DELETE", credentials: "include" });
      await queryClient.invalidateQueries({ queryKey: ["books"] });
      navigate("/books", { replace: true });
    } catch (error) {
      setDeleteError(errorMessage(error, t("book.deleteFailed"), t));
    }
  }

  async function removeAsset(asset: UploadedFile) {
    setFileError(null);
    try {
      await apiRequest(`/api/files/${asset.id}`, { method: "DELETE" });
      setAssets((current) => current.filter((item) => item.id !== asset.id));
    } catch {
      setFileError(t("book.fileDeleteFailed"));
    }
  }

  function addAsset(asset: UploadedFile) {
    setFileError(null);
    setAssets((current) => asset.kind === "BOOK_COVER" ? [...current.filter((item) => item.kind !== "BOOK_COVER"), asset] : [...current, asset]);
  }

  return (
    <section className="mx-auto max-w-4xl">
      <LinkButton size="sm" to="/books" variant="ghost">{t("book.back")}</LinkButton>
      <Card className="mt-6 p-8 sm:p-10">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <Badge variant="accent">{book.category}</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">{book.title}</h1>
            <p className="mt-2 text-lg text-muted">{book.author}</p>
          </div>
          <Badge variant={book.available_copies > 0 ? "success" : "neutral"}>{formatAvailability(book, t)}</Badge>
        </div>
        <div className="mt-8 grid gap-8 border-t border-line pt-8 sm:grid-cols-[1fr_16rem]">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">{t("book.about")}</h2>
            <p className="mt-3 whitespace-pre-wrap leading-7 text-ink-soft">{book.description}</p>
          </div>
          <dl className="space-y-3 text-sm text-muted">
            <div className="flex justify-between gap-4"><dt>{t("catalog.categoryField")}</dt><dd className="font-medium text-ink">{book.category}</dd></div>
            {book.publication_year ? <div className="flex justify-between gap-4"><dt>{t("book.published")}</dt><dd className="font-medium text-ink">{book.publication_year}</dd></div> : null}
            {book.isbn ? <div className="flex justify-between gap-4"><dt>{t("catalog.isbnField")}</dt><dd className="font-medium text-ink">{book.isbn}</dd></div> : null}
          </dl>
        </div>
        <div className="mt-8 border-t border-line pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">{t("book.borrowSection")}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {user ? (
              <Button
                disabled={isBorrowing || book.available_copies === 0}
                loading={isBorrowing}
                onClick={() => void borrowBook()}
                type="button"
              >
                {isBorrowing ? t("book.borrowing") : book.available_copies > 0 ? t("book.borrow") : t("book.currentlyUnavailable")}
              </Button>
            ) : (
              <LinkButton to="/login" variant="accent">{t("book.loginToBorrow")}</LinkButton>
            )}
          </div>
          {borrowMessage ? <Notice className="mt-3" message={borrowMessage} /> : null}
          {borrowError ? <ErrorAlert className="mt-3" message={borrowError} /> : null}
        </div>
        {canManageBooks(user?.role) ? (
          <div className="mt-8 border-t border-line pt-6">
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => setEditing((current) => !current)} variant="secondary" type="button">{editing ? t("book.closeEditor") : t("book.edit")}</Button>
              <Button onClick={() => void removeBook()} variant="danger" type="button">{t("book.delete")}</Button>
            </div>
            {deleteError ? <ErrorAlert className="mt-3" message={deleteError} /> : null}
            {editing ? <BookForm book={book} onCancel={() => setEditing(false)} onSaved={(saved) => { setEditing(false); queryClient.setQueryData(["books", bookId], { book: saved }); }} /> : null}
            <div className="mt-8 border-t border-line pt-6">
              <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-muted">{t("book.filesTitle")}</h2>
              <p className="mt-2 text-sm text-muted">{t("book.filesDescription")}</p>
              <div className="mt-4 space-y-3">
                <FileUpload accept="image/jpeg,image/png,image/webp" endpoint={`/api/books/${book.id}/files`} fields={{ kind: "BOOK_COVER" }} helper={t("file.imageHelper")} label={t("file.cover")} onUploaded={addAsset} />
                <FileUpload accept="application/pdf" endpoint={`/api/books/${book.id}/files`} fields={{ kind: "BOOK_DOCUMENT" }} helper={t("file.pdfHelper")} label={t("file.document")} onUploaded={addAsset} />
              </div>
              {fileError ? <ErrorAlert className="mt-3" message={fileError} /> : null}
              {assets.length > 0 ? (
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  {assets.map((asset) => (
                    <div className="rounded-control border border-line p-3" key={asset.id}>
                      {asset.mime_type.startsWith("image/") ? <img alt={asset.original_filename} className="h-40 w-full rounded-control object-cover" src={asset.url} /> : <a className="block rounded-control bg-canvas p-6 font-medium text-accent-800 hover:text-accent-900" href={asset.url}>{asset.original_filename}</a>}
                      <div className="mt-3 flex items-center justify-between gap-3 text-sm">
                        <span className="truncate text-muted">{asset.original_filename}</span>
                        <Button className="shrink-0" onClick={() => void removeAsset(asset)} size="sm" type="button" variant="danger">{t("book.deleteFile")}</Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </Card>
    </section>
  );
}
