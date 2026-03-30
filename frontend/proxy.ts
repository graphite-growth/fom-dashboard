import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "session_token";

export default function proxy(request: NextRequest) {
  const hasCookie = request.cookies.has(COOKIE_NAME);
  const { pathname } = request.nextUrl;

  // Protected routes: redirect to login if no cookie
  if (pathname.startsWith("/app") && !hasCookie) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Landing page: redirect to /app (authenticated) or /login (unauthenticated)
  if (pathname === "/") {
    return NextResponse.redirect(new URL(hasCookie ? "/app" : "/login", request.url));
  }

  // Redirect authenticated users away from login
  if (pathname === "/login" && hasCookie) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\.png$).*)"],
};
