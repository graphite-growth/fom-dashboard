"use client";

import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useSearchParams } from "next/navigation";

const ERROR_MESSAGES: Record<string, string> = {
  domain_not_allowed: "Your email domain is not authorized to access this application.",
  no_user_info: "Could not retrieve your account information from Google.",
};

export default function LoginForm() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Login to your account</CardTitle>
        <CardDescription>
          Enter your email below to login to your account
        </CardDescription>
      </CardHeader>
      {error && (
        <div className="px-6 pb-2 text-sm text-red-600">
          {ERROR_MESSAGES[error] || "An unexpected authentication error occurred."}
        </div>
      )}
      <CardFooter className="flex-col gap-2">
        <Button variant="outline" className="w-full" asChild>
          <a href="/api/v1/auth/login">
            Login with Google
          </a>
        </Button>
      </CardFooter>
    </Card>
  )
}
