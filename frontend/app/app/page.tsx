import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getUser } from "@/lib/auth";
import { fetchDashboardData } from "@/lib/fetch-dashboard";
import App from "@/app/ui/app";

export default async function Page() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  const user = await getUser(cookieHeader);

  if (!user) {
    // Clear potentially corrupt cookie via backend logout before redirecting to login
    redirect("/api/v1/auth/logout");
  }

  const data = await fetchDashboardData(cookieHeader);

  return <App user={user} data={data} />;
}
