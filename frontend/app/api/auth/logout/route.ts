// Next.js API Route: Logout endpoint
// This file handles logout requests on the server side
// Location: app/api/auth/logout/route.ts

import { NextResponse } from "next/server";

// Get the backend URL from environment variables
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// POST function: Handles POST requests to /api/auth/logout
export async function POST(request: Request) {
  try {
    // Get the user's cookies from the incoming request
    // These cookies contain the session ID that identifies the logged-in user
    const cookieHeader = request.headers.get("cookie");

    // Send logout request to Flask backend
    // Important: We pass the cookies so Flask knows which user to log out
    const response = await fetch(`${BACKEND_URL}/api/auth/logout`, {
      method: "POST",
      // Only include Cookie header if cookies exist
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include", // Include cookies in request
    });

    const data = await response.json();

    // Get any "set-cookie" headers from Flask
    // Flask will send a cookie to clear/invalidate the session
    const cookies = response.headers.get("set-cookie");
    const nextResponse = NextResponse.json(data, { status: response.status });

    // Forward the session-clearing cookie to the browser
    // This removes the session cookie from the user's browser
    if (cookies) {
      nextResponse.headers.set("Set-Cookie", cookies);
    }

    return nextResponse;
  } catch (error) {
    // Handle any errors (network issues, backend down, etc.)
    return NextResponse.json(
      { success: false, error: "Failed to connect to authentication server" },
      { status: 500 },
    );
  }
}
