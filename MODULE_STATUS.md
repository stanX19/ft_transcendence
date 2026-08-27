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
- Custom design system: `S20260827T211805Z_T086-T087_design-system-components`
- Three-language i18n: `S20260827T213411Z_T088-T089-T090_i18n-three-language`
- PWA installability/offline shell: `S20260827T221656Z_T091-T092_pwa-installable-offline`
- Responsive/console-clean sweep: `S20260827T231356Z_T093_responsive-console-sweep`
- Final stretch/documentation gate: `S20260827T232206Z_T094_stretch-documentation-gate`

The latest baseline verification recorded 168 backend tests passing and 25
frontend tests passing in the web image build. A live Gemini credential is
intentionally not required for automated verification; the manual provider
smoke check remains an evaluator step.

## Claimed stretch: 3 points

| Module | Type | Points | Implementation evidence | Contributor record |
|---|---|---:|---|---|
| Custom design system | Minor | 1 | 13 project-owned UI primitives, semantic palette/tokens, documented typography/elevation, focused component tests, and responsive screenshots; `S20260827T211805Z_T086-T087_design-system-components`, `S20260827T231356Z_T093_responsive-console-sweep` | Shan Chien Git identity; human attribution TBD |
| PWA | Minor | 1 | Valid standalone manifest, real 192/512 icons, service worker, cached hashed shell assets, offline navigation/status proof, and protected API cache bypass; `S20260827T221656Z_T091-T092_pwa-installable-offline` | Shan Chien Git identity; human attribution TBD |
| 3-language i18n | Minor | 1 | Complete typed English/Malay/Chinese dictionaries, locale switcher, document language updates, explicit-choice persistence, focused tests, and live language-switch screenshot; `S20260827T213411Z_T088-T089-T090_i18n-three-language` | Shan Chien Git identity; human attribution TBD |
| **Total stretch** |  | **3** |  |  |

## Total claimed: 19 points

The stretch claims above are intentionally limited to the three planned
modules with passed implementation evidence. No other stretch module is
claimed.
