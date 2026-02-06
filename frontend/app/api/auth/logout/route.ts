import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/auth/logout`, {
      method: "POST",
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include",
    });

    const data = await response.json();

    // Forward any Set-Cookie headers (like clearing the session)
    const cookies = response.headers.get("set-cookie");
    const nextResponse = NextResponse.json(data, { status: response.status });

    if (cookies) {
      nextResponse.headers.set("Set-Cookie", cookies);
    }

    return nextResponse;
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to authentication server" },
      { status: 500 },
    );
  }
}
