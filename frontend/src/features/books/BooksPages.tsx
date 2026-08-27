import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, apiRequest } from "../../shared/api";
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

function formatAvailability(book: Book): string {
  return `${book.available_copies} available of ${book.total_copies}`;
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 409) {
    return "That catalog change conflicts with existing inventory.";
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
      setError(errorMessage(saveError, "We could not save this book. Please try again."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="mt-6 space-y-4 rounded-2xl border border-sky-100 bg-sky-50/50 p-5" onSubmit={submit}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-950">{book ? "Edit book" : "Add book"}</h2>
        {onCancel ? (
          <button className="text-sm font-medium text-slate-600 hover:text-slate-950" onClick={onCancel} type="button">
            Cancel
          </button>
        ) : null}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium text-slate-800">
          Title
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" minLength={1} onChange={(event) => update("title", event.target.value)} required value={values.title} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Author
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" minLength={1} onChange={(event) => update("author", event.target.value)} required value={values.author} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Category
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" minLength={1} onChange={(event) => update("category", event.target.value)} required value={values.category} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          ISBN <span className="font-normal text-slate-500">(optional)</span>
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" onChange={(event) => update("isbn", event.target.value)} value={values.isbn} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Publication year <span className="font-normal text-slate-500">(optional)</span>
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" max={3000} min={0} onChange={(event) => update("publication_year", event.target.value)} type="number" value={values.publication_year} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Total copies
          <input className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" min={0} onChange={(event) => update("total_copies", event.target.value)} required type="number" value={values.total_copies} />
        </label>
      </div>
      <label className="block text-sm font-medium text-slate-800">
        Description
        <textarea className="mt-2 min-h-28 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" minLength={1} onChange={(event) => update("description", event.target.value)} required value={values.description} />
      </label>
      {error ? <p className="text-sm text-rose-700" role="alert">{error}</p> : null}
      <button className="rounded-xl bg-slate-950 px-4 py-2.5 font-medium text-white disabled:opacity-60" disabled={isSaving} type="submit">
        {isSaving ? "Saving…" : book ? "Save changes" : "Add book"}
      </button>
    </form>
  );
}

function BookCard({ book }: { book: Book }) {
  return (
    <Link className="block rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300" to={`/books/${book.id}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-sky-700">{book.category}</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950">{book.title}</h2>
          <p className="mt-1 text-sm text-slate-600">{book.author}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${book.available_copies > 0 ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
          {book.available_copies > 0 ? "Available" : "Checked out"}
        </span>
      </div>
      <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-600">{book.description}</p>
      <p className="mt-4 text-sm font-medium text-slate-700">{formatAvailability(book)}</p>
    </Link>
  );
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-2 text-slate-600">{detail}</p>
    </div>
  );
}

export function BooksPage() {
  const { user } = useAuth();
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
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">Library catalog</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Browse books</h1>
          <p className="mt-3 max-w-2xl text-slate-600">Search the local collection by title, author, description, or ISBN.</p>
        </div>
        {canManageBooks(user?.role) ? (
          <button className="rounded-xl bg-slate-950 px-4 py-2.5 font-medium text-white" onClick={() => setShowCreate((current) => !current)} type="button">
            {showCreate ? "Close form" : "Add book"}
          </button>
        ) : null}
      </div>

      {showCreate ? (
        <BookForm
          onCancel={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false);
            void queryClient.invalidateQueries({ queryKey: ["books"] });
          }}
        />
      ) : null}

      <form className="mt-8 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5" onSubmit={search}>
        <label className="text-sm font-medium text-slate-800 lg:col-span-2">
          Search catalog
          <input className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5" onChange={(event) => setSearchInput(event.target.value)} placeholder="Title, author, topic, ISBN" value={searchInput} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Author
          <input className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5" onChange={(event) => updateFilter("author", event.target.value)} placeholder="Filter author" value={filters.author} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Category
          <input className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5" onChange={(event) => updateFilter("category", event.target.value)} placeholder="Filter category" value={filters.category} />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Availability
          <select className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" onChange={(event) => updateFilter("available", event.target.value)} value={filters.available}>
            <option value="all">All books</option>
            <option value="true">Available now</option>
            <option value="false">Checked out</option>
          </select>
        </label>
        <label className="text-sm font-medium text-slate-800">
          Sort by
          <select className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5" onChange={(event) => updateFilter("sort", event.target.value)} value={filters.sort}>
            <option value="title">Title</option>
            <option value="author">Author</option>
            <option value="newest">Newest</option>
          </select>
        </label>
        <button className="rounded-xl bg-sky-700 px-4 py-2.5 font-medium text-white hover:bg-sky-800 sm:col-span-2 lg:col-span-5 lg:justify-self-end" type="submit">Search</button>
      </form>

      {booksQuery.isLoading ? <PageMessage title="Loading catalog…" detail="Fetching books from the library collection." /> : null}
      {booksQuery.error ? <PageMessage title="Catalog unavailable" detail="We could not load the books. Please try again." /> : null}
      {booksQuery.data && booksQuery.data.items.length === 0 ? <PageMessage title="No books found" detail="Try a broader search or clear one of the filters." /> : null}
      {booksQuery.data && booksQuery.data.items.length > 0 ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {booksQuery.data.items.map((book) => <BookCard book={book} key={book.id} />)}
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 text-sm text-slate-600">
            <span>Page {booksQuery.data.page} of {totalPages} · {booksQuery.data.total} books</span>
            <div className="flex gap-2">
              <button className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40" disabled={filters.page <= 1} onClick={() => pageChange(filters.page - 1)} type="button">Previous</button>
              <button className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40" disabled={filters.page >= totalPages} onClick={() => pageChange(filters.page + 1)} type="button">Next</button>
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
  const [editing, setEditing] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [borrowError, setBorrowError] = useState<string | null>(null);
  const [borrowMessage, setBorrowMessage] = useState<string | null>(null);
  const [isBorrowing, setIsBorrowing] = useState(false);
  const bookQuery = useQuery({
    queryKey: ["books", bookId],
    queryFn: () => apiRequest<BookResponse>(`/api/books/${bookId}`),
    enabled: Boolean(bookId),
    refetchInterval: 30_000,
    retry: false,
  });
  const book = bookQuery.data?.book;

  if (bookQuery.isLoading) return <PageMessage title="Loading book…" detail="Fetching the catalog record." />;
  if (bookQuery.error) {
    const notFound = bookQuery.error instanceof ApiError && bookQuery.error.status === 404;
    return <PageMessage title={notFound ? "Book not found" : "Book unavailable"} detail={notFound ? "This catalog record does not exist." : "Please try again in a moment."} />;
  }
  if (!book) return <PageMessage title="Book unavailable" detail="No catalog data was returned." />;

  async function borrowBook() {
    setBorrowError(null);
    setBorrowMessage(null);
    setIsBorrowing(true);
    try {
      await apiRequest(`/api/books/${book.id}/borrow`, { method: "POST" });
      setBorrowMessage("Loan recorded. This book is now in My loans.");
      await queryClient.invalidateQueries({ queryKey: ["books"] });
      await queryClient.invalidateQueries({ queryKey: ["loans", "me"] });
    } catch (error) {
      setBorrowError(
        error instanceof ApiError && error.status === 409
          ? "This book is no longer available for you to borrow."
          : "We could not borrow this book. Please try again.",
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
      setDeleteError(errorMessage(error, "We could not delete this book. Please try again."));
    }
  }

  return (
    <section className="mx-auto max-w-4xl">
      <Link className="text-sm font-medium text-sky-700 hover:text-sky-900" to="/books">← Back to catalog</Link>
      <div className="mt-6 rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">{book.category}</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{book.title}</h1>
            <p className="mt-2 text-lg text-slate-600">{book.author}</p>
          </div>
          <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700">{formatAvailability(book)}</span>
        </div>
        <div className="mt-8 grid gap-8 border-t border-slate-100 pt-8 sm:grid-cols-[1fr_16rem]">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">About this book</h2>
            <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-700">{book.description}</p>
          </div>
          <dl className="space-y-3 text-sm text-slate-600">
            <div className="flex justify-between gap-4"><dt>Category</dt><dd className="font-medium text-slate-950">{book.category}</dd></div>
            {book.publication_year ? <div className="flex justify-between gap-4"><dt>Published</dt><dd className="font-medium text-slate-950">{book.publication_year}</dd></div> : null}
            {book.isbn ? <div className="flex justify-between gap-4"><dt>ISBN</dt><dd className="font-medium text-slate-950">{book.isbn}</dd></div> : null}
          </dl>
        </div>
        <div className="mt-8 border-t border-slate-100 pt-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Borrow this book</h2>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {user ? (
              <button
                className="rounded-xl bg-sky-700 px-4 py-2.5 font-medium text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isBorrowing || book.available_copies === 0}
                onClick={() => void borrowBook()}
                type="button"
              >
                {isBorrowing ? "Borrowing…" : book.available_copies > 0 ? "Borrow book" : "Currently unavailable"}
              </button>
            ) : (
              <Link className="rounded-xl bg-sky-700 px-4 py-2.5 font-medium text-white hover:bg-sky-800" to="/login">Log in to borrow</Link>
            )}
          </div>
          {borrowMessage ? <p className="mt-3 text-sm text-emerald-700" role="status">{borrowMessage}</p> : null}
          {borrowError ? <p className="mt-3 text-sm text-rose-700" role="alert">{borrowError}</p> : null}
        </div>
        {canManageBooks(user?.role) ? (
          <div className="mt-8 border-t border-slate-100 pt-6">
            <div className="flex flex-wrap gap-3">
              <button className="rounded-xl border border-slate-300 px-4 py-2.5 font-medium text-slate-700" onClick={() => setEditing((current) => !current)} type="button">{editing ? "Close editor" : "Edit book"}</button>
              <button className="rounded-xl border border-rose-200 px-4 py-2.5 font-medium text-rose-700" onClick={() => void removeBook()} type="button">Delete book</button>
            </div>
            {deleteError ? <p className="mt-3 text-sm text-rose-700" role="alert">{deleteError}</p> : null}
            {editing ? <BookForm book={book} onCancel={() => setEditing(false)} onSaved={(saved) => { setEditing(false); queryClient.setQueryData(["books", bookId], { book: saved }); }} /> : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
