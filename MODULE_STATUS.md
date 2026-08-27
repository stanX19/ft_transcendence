# Module status

This ledger counts only behavior that is implemented, tested, and
demonstrable in the current repository. The evidence sessions referenced
below are kept in the outer workspace so they do not pollute the submission
Git history.

## Claimed baseline: 16 points

| Module | Type | Points | Implementation evidence | Contributor record |
|---|---|---:|---|---|
| Frontend + backend frameworks | Major | 2 | React/TypeScript/Vite frontend and FastAPI/Python backend, deployed through Docker Compose/Nginx | Shan Chien Git identity; human attribution TBD |
| Public database API | Major | 2 | `/public-api/v1` API-key-protected catalog CRUD, OpenAPI docs, database operations, and rate limiting | Shan Chien Git identity; human attribution TBD |
| ORM | Minor | 1 | SQLAlchemy 2.x models, repositories/services, PostgreSQL foreign keys and constraints, Alembic migrations | Shan Chien Git identity; human attribution TBD |
| Advanced search | Minor | 1 | Full-text search, author/category/availability filters, sort options, and bounded pagination | Shan Chien Git identity; human attribution TBD |
| File upload/management | Minor | 1 | Avatar/cover/PDF upload, Pillow/PDF validation, safe storage/access, preview, progress, and deletion | Shan Chien Git identity; human attribution TBD |
| Standard user management | Major | 2 | Profiles, avatars/default avatar, direct friendships, friend list, and online status | Shan Chien Git identity; human attribution TBD |
| Advanced permissions | Major | 2 | Backend-enforced MEMBER/LIBRARIAN/ADMIN roles, admin user CRUD/role management, and protected catalog/file actions | Shan Chien Git identity; human attribution TBD |
| Complete RAG system | Major | 2 | PostgreSQL full-text retrieval, bounded local catalog context, Gemini provider boundary, and visible retrieved source books | Shan Chien Git identity; human attribution TBD |
| Complete LLM interface | Major | 2 | Gemini text generation, authenticated POST-SSE token streaming, safe provider errors, and separate per-user AI limit | Shan Chien Git identity; human attribution TBD |
| Data import/export | Minor | 1 | CSV/JSON/XML export and transactional validated bulk import with row-level errors | Shan Chien Git identity; human attribution TBD |
| **Total** |  | **16** |  |  |

## Evidence checkpoints

- Foundation/auth/users/legal: `S20260827T155801Z_T013-T014-T015-T016-T017-T018-T019-T020-T021-T022-T023-T024_auth-users-legal`
- Catalog/search: `S20260827T165954Z_T025-T026-T027-T028-T029-T030-T031-T032-T033-T034-T035-T036-T037-T038_catalog-search`
- Loans/concurrency: `S20260827T175604Z_T039-T040-T041-T042-T043-T044-T045-T046-T047_loans-concurrency`
- Users/files/friends/permissions: `S20260827T181345Z_T048-T049-T050-T051-T052-T053-T054-T055-T056-T057-T058-T059_users-files-permissions`
- Public API: `S20260827T184853Z_T060-T061-T062-T063-T064-T065-T066_public-api`
- Data exchange: `S20260827T190340Z_T067-T068-T069-T070_data-import-export`
- Public API/data documentation gate: `S20260827T193455Z_T071_public-api-data-gate`
- RAG/provider: `S20260827T193928Z_T072-T073-T074-T075-T076_rag-backend`
- Tools/orchestration/SSE: `S20260827T200307Z_T077-T078-T079-T080-T081_ai-tools-orchestration-stream`
- Assistant UI/AI safeguards gate: `S20260827T201946Z_T082-T083-T084-T085_assistant-ui-and-ai-gate`

The latest baseline verification recorded 166 backend tests passing and 20
frontend tests passing in the web image build. A live Gemini credential is
intentionally not required for automated verification; the manual provider
smoke check remains an evaluator step.

## Stretch modules not claimed

The design-system, i18n/multiple-language, and PWA modules remain unclaimed
until their implementation, regression checks, and documentation are
complete. This keeps the score ledger conservative.
