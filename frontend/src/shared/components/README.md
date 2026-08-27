# LibraryOS UI system

The shared layer is intentionally small and project-owned. It centralizes the
restrained light palette, system typography, control radii, focus treatment,
status colors, and Lucide icon usage without introducing a component
framework.

## Components

`Button`, `LinkButton`, `Card`, `Badge`, `Input`, `Select`, `TextArea`,
`FormField`, `PageHeader`, `LoadingState`, `EmptyState`, `ErrorAlert`, and
`Notice` are the reusable vocabulary. The application shell, authentication,
and catalog pages use the system today; the same vocabulary is the migration
path for loans, users, friends, admin, data exchange, legal, file, and
assistant pages.

Use `Button` for actions and `LinkButton` for navigation. Use the field
components with `FormField` so labels and focus states stay consistent. Use
`LoadingState`, `EmptyState`, `ErrorAlert`, and `Notice` for explicit server
state instead of inventing one-off messages. Lucide React is the only icon
source.

The semantic Tailwind colors are backed by CSS variables in `src/index.css`
and exposed through `tailwind.config.js`. Add a token only when it has a
semantic role and is used more than once.
