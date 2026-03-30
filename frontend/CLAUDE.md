# Frontend Context

Next.js 16 App Router application with TypeScript. Uses Bun as the package manager.

## Standards

- TypeScript required for all components and functions
- ESLint configuration enforced
- Run type checking after making code changes: `bun run lint`

## Commands

- Install dependencies: `bun install`
- Development server: `bun dev`
- Build: `bun run build`

## Authentication

- Backend-owned via `/api/v1/auth/*` endpoints (Google OAuth login, callback, logout)
- Sessions use HTTP-only `session_token` cookies containing JWTs
- `proxy.ts` middleware protects `/app` routes by checking for the session cookie
- Use `getUser()` from `lib/auth.ts` in server components to fetch the current user
- **Dev bypass:** Start the backend with `DEV_AUTH=true` to skip Google OAuth. The backend auto-creates a session cookie for a fake user (`dev@example.com`), so no Google credentials are needed for local development.

## Backend Communication

All backend calls go through `BACKEND_URL` (set in `lib/config.ts`, defaults to `http://localhost:8000`).

- **Client-side**: Always use relative URLs (`/api/v1/...`). Next.js rewrites in `next.config.ts` proxy these to `BACKEND_URL`. Never import `BACKEND_URL` in client components.
- **Server-side**: Import `BACKEND_URL` from `@/lib/config` and call the backend directly.
- **Docker**: `docker-compose.yml` sets `BACKEND_URL=http://backend:8000`. No changes needed.
- **Local dev** (`bun dev`): The default `http://localhost:8000` works if the backend runs on port 8000.

## UI Components

This project uses **shadcn/ui** for all UI components (`components/ui/`). No alternative UI libraries (MUI, Chakra, Ant Design, Headless UI, React Aria).

- Add new components: `bunx --bun shadcn@latest add <component-name>`
- Import from `@/components/ui/<component>`, not directly from `radix-ui`
- Extend components with CVA variants rather than creating new files
- Icons: `lucide-react` only
- Do not delete `components.json`
