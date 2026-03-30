import * as jose from "jose";

export interface User {
  name: string;
  email: string;
  image: string;
}

const AUTH_SECRET = process.env.AUTH_SECRET || "";

export async function getUser(cookieHeader: string): Promise<User | null> {
  // Extract session_token from cookie header
  const match = cookieHeader.match(/session_token=([^;]+)/);
  if (!match) return null;

  try {
    const secret = new TextEncoder().encode(AUTH_SECRET);
    const { payload } = await jose.jwtVerify(match[1], secret, {
      algorithms: ["HS256"],
    });
    return {
      name: (payload.name as string) || "",
      email: (payload.email as string) || "",
      image: (payload.picture as string) || "",
    };
  } catch (e) {
    console.log("[getUser] JWT verify failed", e);
    return null;
  }
}
