# Frontend

Next.js application providing the web UI for **fom-dashboard**.

## Prerequisites

- [Bun](https://bun.sh/) (package manager and runtime)

## Getting Started

```bash
bun install
bun dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

## Architecture

- **Framework:** Next.js 16 with App Router
- **Language:** TypeScript
- **UI primitives:** Radix UI (wrapped in `components/ui/`)
- **Styling:** Tailwind CSS v4 with CSS variables for theming
- **Icons:** lucide-react
- **Auth:** Backend-owned JWT auth with Google OAuth (no NextAuth)

## Project Structure

```
app/
  layout.tsx          # Root layout (metadata, fonts)
  globals.css         # Tailwind theme & CSS variables
  app/page.tsx        # /app route (authenticated dashboard)
  login/page.tsx      # /login route
  ui/
    app.tsx           # Dashboard UI (sidebar + API example)
    login-form.tsx    # Login form component
components/
  app-sidebar.tsx     # Sidebar shell (logo + user nav)
  nav-user.tsx        # User dropdown menu
  ui/                 # Radix UI styled wrappers
hooks/
  use-mobile.ts       # Mobile breakpoint hook
lib/
  auth.ts             # getUser() server-side auth helper
  utils.ts            # cn() class merge utility
proxy.ts              # Middleware (route protection, cookie checks)
```

## Authentication Flow

1. Unauthenticated users are redirected to `/login` by the middleware (`proxy.ts`)
2. Clicking "Login with Google" navigates to `/api/v1/auth/login` (backend)
3. Backend handles the Google OAuth flow and sets an HTTP-only `session_token` cookie
4. Middleware detects the cookie and allows access to `/app` routes
5. Server components use `getUser()` from `lib/auth.ts` to fetch the current user
