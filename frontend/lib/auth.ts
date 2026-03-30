import { BACKEND_URL } from "./config";

export interface User {
  name: string;
  email: string;
  image: string;
}

export async function getUser(cookieHeader: string): Promise<User | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/auth/me`, {
      headers: { cookie: cookieHeader },
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as User;
  } catch {
    return null;
  }
}
