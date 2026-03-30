import { BACKEND_URL } from "./config";

export interface User {
  name: string;
  email: string;
  image: string;
}

export async function getUser(cookieHeader: string): Promise<User | null> {
  const url = `${BACKEND_URL}/auth/me`;
  try {
    console.log("[getUser] fetching", url);
    const response = await fetch(url, {
      headers: { cookie: cookieHeader },
    });
    console.log("[getUser] status", response.status);
    if (!response.ok) {
      const body = await response.text();
      console.log("[getUser] error body", body);
      return null;
    }
    return (await response.json()) as User;
  } catch (e) {
    console.log("[getUser] exception", e);
    return null;
  }
}
