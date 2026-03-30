import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");
  if (!token) {
    return NextResponse.redirect(new URL("/login?error=no_token", request.url));
  }

  const response = NextResponse.redirect(new URL("/app", request.url));
  response.cookies.set("session_token", token, {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 60 * 60 * 24, // 24 hours
  });
  return response;
}
