import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getUser } from "@/lib/auth";
import AppWithData from "./app-with-data";

export default async function Page() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  const user = await getUser(cookieHeader);

  if (!user) {
    redirect("/api/v1/auth/logout");
  }

  return <AppWithData user={user} />;
}
