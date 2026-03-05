import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(request: Request) {
  try {
    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/auth/session`, {
      method: "GET",
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include",
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        authenticated: false,
        error: "Failed to connect to authentication server",
      },
      { status: 500 },
    );
  }
}
