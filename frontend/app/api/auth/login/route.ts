import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: "Email and password are required" },
        { status: 400 },
      );
    }

    // Call Flask backend API
    const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    // Forward session cookies from Flask to browser
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
