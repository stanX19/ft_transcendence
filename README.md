# LibraryOS

LibraryOS is a Library Management System for `ft_transcendence`. It provides
catalog discovery, safe borrowing, profiles and friendships, secure file
management, a documented public API, catalog import/export, and a
catalog-grounded Gemini assistant.

## Team and attribution

The current repository history contains one Git author identity: **Shan
Chien**. The checkout does not contain a confirmed team roster, role
assignment, or communication record. The table below is deliberately explicit
about the remaining human information that must be completed by the team
before submission; it must not be inferred from automated commits.

| Person | PO | PM / Scrum Master | Tech Lead / Architect | Developer | Recorded responsibility |
|---|---|---|---|---|---|
| Shan Chien | TBD | TBD | TBD | TBD | Git author on the current repository history; confirm the human role assignment |
| Additional team member(s) | TBD | TBD | TBD | TBD | Add actual names and responsibilities before evaluation |

The implementation was organized as small vertical slices: foundation and
authentication, catalog/search, loans and concurrency, users/files/friends and
permissions, public API, data exchange, RAG/provider, and the assistant UI.
Each slice was tested against PostgreSQL, reviewed, and checkpointed in Git.
The project-management tool/process and communication channel are **TBD** in
this checkout because no human team record was supplied. The outer planning
workspace keeps the requirements, backlog, review notes, and QA evidence
outside the submitted repository.

## Local startup

From this directory:

```bash
cp .env.example .env
# Replace AUTH_SECRET and PUBLIC_API_KEY before a shared or production run.
docker compose up --build
```

Open <https://localhost>. The local certificate is self-signed for
development. A browser may show a trust warning on first visit; accepting the
local exception is sufficient for local evaluation. The certificate is kept
in the named `certs_data` volume, so recreating the web container does not
silently replace a certificate that has already been trusted.

For a persistent OS/browser trust setup, copy the public certificate out of
the running container and import only that certificate into the local trust
store:

```bash
docker compose cp web:/etc/nginx/certs/localhost.crt ./localhost.crt
```

Never copy or import the private key. The certificate covers `localhost` and
`127.0.0.1`; use the matching hostname when opening the application.

With `SEED_DEMO_DATA=true`, startup deterministically creates 600 catalog
records from the checked-in generator in `backend/app/seed.py`. The records
are not stored in Git as a database dump: a teammate cloning the repository
gets the same catalog by running `docker compose up --build`, while their
PostgreSQL named volume remains local to their machine.

The API is intentionally not published as a host port. Browser traffic goes
through Nginx over HTTPS, and backend secrets remain in the API container.

### Local evaluator accounts

With `SEED_DEMO_DATA=true` (the local `.env.example` default), startup creates
these reserved evaluation accounts. They use the non-routable `example.test`
domain and are for local rehearsal only; set `SEED_DEMO_DATA=false` for a
shared or production deployment and never reuse these passwords.

| Role | Email | Password |
|---|---|---|
| Member | `member.demo@example.test` | `LibraryOS-member-demo-2026!` |
| Librarian | `librarian.demo@example.test` | `LibraryOS-librarian-demo-2026!` |
| Admin | `admin.demo@example.test` | `LibraryOS-admin-demo-2026!` |

## Technical stack and rationale

- **Frontend:** React, TypeScript, Vite, React Router, TanStack Query,
  Tailwind CSS, Lucide React, Vitest, and React Testing Library. React keeps
  the evaluator-facing pages explicit; TanStack Query handles server state;
  Tailwind and project-owned components keep the dependency surface small.
- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy
  2.x, Alembic, Psycopg, PyJWT, `pwdlib[argon2]`, Pillow, and `google-genai`.
  FastAPI provides ordinary REST/OpenAPI behavior, while SQLAlchemy and
  Alembic keep database rules and migrations visible.
- **Database:** PostgreSQL 16. It supplies transactions and row locking for
  final-copy borrowing, partial unique indexes for active loans, and ranked
  full-text search for local RAG without a vector extension.
- **Runtime:** Docker Compose with `web`, `api`, and `db`. Nginx is the only
  browser-facing service and serves the React build, HTTPS, and reverse-proxy
  routes. FastAPI stays private on the Compose network.
- **Authentication:** a signed JWT in the `Secure`, `HttpOnly`,
  `SameSite=Lax` `libraryos_session` cookie. Tokens are not stored in browser
  local or session storage.
- **AI:** the Gemini SDK is isolated under `backend/app/features/ai/`.
  PostgreSQL full-text retrieval supplies bounded catalog context, safe
  authenticated tools supply account facts, and the browser consumes the
  assistant through credentialed POST-SSE streaming `fetch()`. Configure
  `GEMINI_API_KEY_LIST` as a JSON array in `.env`; the provider advances to
  the next key only on HTTP 429, wraps around, and allows three retries after
  the initial request. The assistant tools are read-only: catalog details,
  current availability, the authenticated user's loans, and safe internal
  page navigation. Navigation only emits a canonical route; borrowing still
  happens explicitly on the book detail page. AI lifecycle logs expose only
  event names, correlation IDs, key indexes, counts, and safe error types.

## Architecture

```text
Browser
  |
  | HTTPS :443
  v
Nginx (static React build + reverse proxy)
  |
  v
FastAPI
  |
  v
PostgreSQL
```

The `/api/ai/chat/stream` route uses `text/event-stream`; Nginx disables
buffering and caching for that route. Uploaded files are served through an
id-based FastAPI endpoint rather than as a raw directory. The frontend reads
`/api/auth/me` to derive authentication state.

## Database schema

All primary keys are integers. Timestamps are timezone-aware UTC values.

| Table | Key fields and constraints | Relationships |
|---|---|---|
| `users` | `id`, unique `email`, Argon2 `password_hash`, `display_name`, `bio`, enum `role` (`MEMBER`, `LIBRARIAN`, `ADMIN`), presence and audit timestamps | Parent of loans, friendships, and user-owned file assets |
| `books` | `id`, nullable unique `isbn`, `slug`, title/author/description/category, publication year, `total_copies`, `available_copies`, generated PostgreSQL `tsvector` search column and GIN index | Parent of loans and book-owned file assets |
| `loans` | `id`, `user_id`, `book_id`, `borrowed_at`, `due_at`, nullable `returned_at`; due-date check and partial unique active `(user_id, book_id)` index | Foreign keys to `users` and `books`; book rows are locked for borrow/return inventory changes |
| `friendships` | `id`, canonical `user_low_id < user_high_id`, unique unordered pair, check constraint | Two foreign keys to `users` |
| `file_assets` | `id`, exactly one nullable owner boundary (`owner_user_id` or `book_id`), kind, original/stored names, MIME, byte size, timestamp; partial unique current avatar/cover indexes | Foreign key to either `users` or `books`; bytes live in the uploads volume |

The public API key, JWT signing secret, and Gemini key are configuration
secrets, not database columns. Alembic migrations and
`backend/app/core/model_registry.py` keep schema changes explicit.

## Implemented features and contributors

The current Git history records the following feature slices under the Shan
Chien Git identity. Human team attribution must be confirmed before the final
submission.

- Registration, login/logout, `/me`, secure password hashing, cookie sessions,
  profile editing, and legal pages (`/privacy`, `/terms`).
- Catalog CRUD for librarians/admins, deterministic local seed data, indexed
  free-text/author/category/availability search, sorting, pagination, and
  inventory invariants.
- Transaction-safe borrowing with a locked final-copy path, active/history
  loan views, duplicate-loan prevention, and idempotent returns.
- Profile avatars, book covers and PDFs with server-generated names, content
  validation, authorization, previews, progress reporting, and deletion.
- Direct add/remove/list friendships and derived online status.
- Admin user listing, role changes, deletion guards, and backend-enforced
  `MEMBER`/`LIBRARIAN`/`ADMIN` permissions.
- API-key-protected `/public-api/v1` catalog CRUD with OpenAPI documentation,
  PostgreSQL-backed operations, and a separate fixed-window rate limit.
- Librarian/admin CSV, JSON, and XML catalog import/export with full-batch
  validation, row-level errors, and transactional writes.
- PostgreSQL full-text catalog retrieval, bounded RAG context, Gemini
  provider isolation, safe tool dispatch, authenticated POST-SSE streaming,
  per-user AI rate limiting, safe assistant navigation, and the `/assistant`
  React page with visible source books, loading, error, and tool-activity
  states. This slice deliberately does not create embeddings or a vector
  database; the catalog's PostgreSQL full-text index is the retrieval store.

## Verification

Backend tests use the separate `libraryos_test` PostgreSQL database and fake
Gemini providers. From `project/`, the production web build is:

```bash
docker compose build web
```

In this orchestration workspace, the isolated backend test helper is one
directory above the submission repository:

```bash
# run from the workspace root, not from project/
bash scripts/api_test.sh -q
```

The web image runs Vitest before the Vite production build. The evaluator
workspace retains session-specific command logs, review notes, and real UI
screenshots outside this Git repository.

## Subject module status

The evidence-based module ledger is in [`MODULE_STATUS.md`](MODULE_STATUS.md).
It claims the demonstrable 19-point plan: the 16-point baseline plus the
custom design system, PWA, and English/Malay/Chinese i18n stretch modules.
Each stretch module has its own implementation, regression, and UI evidence;
the final T094 gate reran 168 backend tests and the Docker web build.

## Individual contribution and challenges

The repository history currently records Shan Chien as the Git author for the
implementation checkpoints. The human team must replace the `TBD` role and
contribution fields above with the real distribution before evaluation; no
automated worker should be presented as a human teammate.

Recorded engineering challenges and their implemented handling include:

- **Final-copy races:** borrow/return operations lock the book row inside a
  transaction and are covered by a real PostgreSQL concurrency test.
- **Safe browser authentication:** session state is derived from `/me` and
  the JWT stays in an HttpOnly cookie rather than browser storage.
- **Untrusted uploads:** Pillow/PDF signature checks, server-generated names,
  bounded size, and application-level file access prevent path and content
  mistakes.
- **Grounded assistant answers:** local PostgreSQL retrieval is performed
  before generation, source records are returned to the UI, and account facts
  are available only through authenticated tools.
- **Streaming/failure behavior:** POST-SSE is parsed progressively in the
  browser, Nginx buffering is disabled, provider failures are translated to
  safe messages, and a process-local per-user AI limit matches the single
  Uvicorn worker contract.

Human-specific challenges, meeting history, communication channel, and
individual work split remain **TBD** because they are not recorded in this
checkout.
