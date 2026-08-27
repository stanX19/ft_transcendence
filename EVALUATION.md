# LibraryOS evaluation runbook

This runbook is for a clean local demonstration of the implemented 16-point
baseline. It explains what to show, where the behavior lives, and which
checks are automated. It does not claim that a human Chrome rehearsal has
already happened.

## Before the demo

From the repository directory:

```bash
cp .env.example .env
# Set non-placeholder local AUTH_SECRET and PUBLIC_API_KEY values.
docker compose up --build
```

Open `https://localhost` and accept the local certificate warning if the
browser asks. The normal startup command waits for PostgreSQL, applies
Alembic migrations, seeds local data/accounts, and starts one Uvicorn worker.

### Local-only evaluator accounts

These accounts are created only when `SEED_DEMO_DATA=true` and are reserved
for local evaluation. They use the reserved `example.test` domain:

| Role | Email | Password |
|---|---|---|
| Member | `member.demo@example.test` | `LibraryOS-member-demo-2026!` |
| Librarian | `librarian.demo@example.test` | `LibraryOS-librarian-demo-2026!` |
| Admin | `admin.demo@example.test` | `LibraryOS-admin-demo-2026!` |

Do not use these credentials in a shared or production deployment. Set
`SEED_DEMO_DATA=false` outside a local evaluation environment.

## Suggested demo sequence

### 1. Authentication and profiles

1. Visit `/register` and create a second temporary member account.
2. Log in at `/login`; show that the application returns to the protected
   shell and that `/api/auth/me` derives the session state.
3. Open `/profile`, edit the display name/bio, upload an avatar, preview it,
   and delete it. Log out and confirm protected pages require authentication.

This demonstrates registration, secure cookie authentication, profile editing,
avatar management, and the default-avatar fallback.

### 2. Catalog, search, and inventory

1. Open `/books` and demonstrate pagination, free-text search, author and
   category filters, availability filtering, and title/author/newest sorting.
2. Open a book detail page and show the current copy count and source links.
3. Log in as the librarian and create or edit a book. Confirm that the member
   account receives a backend `403` for the same privileged write.

The seed contains 600 local records with varied topics, so this flow does not
depend on a remote catalog service.

### 3. Borrowing and concurrency

1. As a member, borrow an available book and open `/loans` to show its due
   date and active-loan state.
2. Return the book and show that the action is idempotent and inventory is
   restored once.
3. For the final-copy race, use the PostgreSQL-backed automated concurrency
   test. It proves that two simultaneous borrowers produce exactly one
   success, one conflict, one active loan, and zero available copies. Two
   browser tabs can be used as an optional visual rehearsal, but the test is
   the authoritative correctness demonstration.

### 4. Friends and online status

1. With two accounts, open `/people`, add the other user as a friend, and show
   the friend in `/friends`.
2. Remove the friendship and show the list update. The list also exposes the
   derived online state from recent activity.

### 5. File management and permissions

1. As the librarian, upload a book cover and PDF from the book detail page;
   show preview/delete behavior and the upload progress indicator.
2. Try the same book-file operation as a member and confirm backend denial.
3. As the admin, open `/admin/users`, change a safe user's role, and show that
   the changed permissions affect backend behavior. The last-admin and
   self-delete protections should remain intact.

Files are stored with server-generated names in the Docker uploads volume and
are served through `GET /api/files/{id}`. The browser never chooses a storage
path.

### 6. Public API and data exchange

Use the configured `PUBLIC_API_KEY` from the local `.env` only in a local
terminal. The public API is separate from the browser session cookie:

```bash
set -a; . ./.env; set +a
curl -k -H "X-API-Key: $PUBLIC_API_KEY" \
  https://localhost/public-api/v1/books?page=1&page_size=5
```

Show the API documentation at `https://localhost/api/docs` or
`https://localhost/api/openapi.json`. Demonstrate a valid key, an invalid key,
the rate-limit response, and a small create/update/delete cycle. Then open
`/admin/import-export` as a librarian and export/import CSV, JSON, and XML;
show that mixed invalid input returns row errors without partial writes.

### 7. RAG and assistant

1. Open `/assistant` as an authenticated user. Submit a catalog question such
   as “Find a science book about careful observation.”
2. Show the loading state, progressive response, and visible source books.
   Open a source link to verify it is a real catalog record.
3. Ask about availability or current loans. Verify important values in the
   regular catalog/loan pages rather than treating generated text as the
   source of truth.
4. If a live `GEMINI_API_KEY` is configured for the rehearsal, show the normal
   response and a provider-failure/error state. If it is absent, the expected
   behavior is a clear assistant configuration error while all non-AI pages
   remain usable.

The automated AI suite uses a fake provider and does not require a network
credential. The current backend tool boundary is allowlisted and carries the
authenticated request user; `get_current_user_loans` cannot receive an
arbitrary user id. The tool-enabled orchestration path calls existing catalog
and loan services, while the POST-SSE path retrieves local sources and streams
provider text to the browser. The client also understands structured tool
activity events if a provider emits them.

## Architecture explanation

```text
Browser
  |
  | HTTPS :443, same-origin cookies
  v
Nginx
  |-- static React build
  |-- /api/*       -> FastAPI
  `-- /public-api/* -> FastAPI
                         |
                         v
                    PostgreSQL 16
```

- Nginx is the only host-facing service. FastAPI is private on the Compose
  network. The stream location disables response buffering/caching so SSE
  chunks arrive progressively.
- FastAPI owns validation, authorization, business rules, tool dispatch, file
  access policy, and OpenAPI routes. SQLAlchemy 2.x and Alembic keep the
  relational schema explicit.
- PostgreSQL owns durable state and important invariants. Borrowing locks the
  book row in a transaction; active duplicate loans use a partial unique
  index; catalog RAG uses a generated `tsvector` and GIN index.
- Browser authentication is a signed JWT in the Secure, HttpOnly,
  SameSite=Lax `libraryos_session` cookie. No access token is placed in
  localStorage or sessionStorage.

### RAG flow

```text
question
  -> PostgreSQL websearch_to_tsquery + ts_rank_cd
  -> bounded catalog records and source metadata
  -> Gemini provider boundary
  -> grounded answer / source events
```

Retrieval is local, deterministic, and ranked by PostgreSQL. The prompt
explicitly tells the provider to use the bounded records and not invent
catalog facts. Inventory, due dates, and account state remain database/tool
facts.

### Tool flow

```text
user question
  -> allowlisted provider function call
  -> authenticated ToolContext
  -> existing books/loans service
  -> authorized PostgreSQL result
  -> provider answer and safe activity metadata
```

There is one tool dispatcher under `backend/app/features/ai/tools.py`; it does
not duplicate catalog or loan business logic. Private loan lookup derives the
user from the request context.

### File and security boundaries

The backend checks upload bytes and size, decodes images with Pillow, checks
PDF signatures, generates stored filenames, and resolves file paths inside the
uploads volume. API keys and Gemini credentials come from environment
settings, never the browser bundle or logs. Provider exceptions are translated
to safe user messages without returning SDK details, stack traces, or keys.

## Automated verification

From the outer orchestration workspace root, the isolated backend helper is:

```bash
bash scripts/api_test.sh -q
```

From `project/`, the frontend acceptance build is:

```bash
docker compose build web
```

The web image runs Vitest before Vite bundling. The focused seed smoke test is
`tests/foundation/test_demo_seed.py`; it logs into all three demo accounts and
checks member/librarian/admin role boundaries. `scripts/https_smoke.sh` checks
the HTTPS `/api/health` entry point. Manual Chrome rehearsal and live Gemini
connectivity are separate human/evaluator steps.

## Small live-modification drills

Each drill is intentionally narrow. Make it on a branch or disposable local
checkout, add/update a focused test, run the relevant suite, and explain the
tradeoff before keeping it.

1. **Add one profile field.** Add a nullable `pronouns` or `website` field in
   `features/users/models.py`, write an Alembic migration, update the users
   schema/service and profile form, then extend the profile API test.
2. **Add one catalog filter.** Add a `publication_year_from` query field in
   the books schemas/repository, expose it in the `/books` controls, and add a
   search contract covering the SQL predicate and pagination total.
3. **Adjust the loan due-date rule.** Change the configured loan duration or
   introduce a small role-specific policy in `features/loans/service.py`, then
   update the loan lifecycle test and explain how existing loans are treated.
4. **Add one public API response field.** Expose a non-sensitive catalog field
   in the public schema, verify it on GET and CRUD responses, and keep the
   internal/public serialization boundaries explicit.
5. **Extend an assistant source card.** Add ISBN display to
   `features/assistant/AssistantPage.tsx`, preserve the existing source
   validation, and update `src/app/assistant.test.tsx` to assert the rendered
   metadata.
6. **Add one evaluator assertion.** Extend
   `tests/foundation/test_demo_seed.py` with a safe invariant such as the
   seeded admin cannot demote itself, then run the focused test and the full
   backend regression.

These drills are practice prompts, not claims that the changes have already
been made. Human team members should record their actual drill and review
history in the final README contribution section.
