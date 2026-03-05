// Next.js API Route: Session check endpoint
// This file checks if a user is currently logged in
// Location: app/api/auth/session/route.ts

import { NextResponse } from "next/server";

// Get the backend URL from environment variables
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// GET function: Handles GET requests to /api/auth/session
// Used to check if user has an active session (is logged in)
export async function GET(request: Request) {
  try {
    // Get the user's cookies from the incoming request
    // The session cookie tells us who the user is
    const cookieHeader = request.headers.get("cookie");

    // Ask Flask backend to verify the session
    // Flask checks if the session cookie is valid and not expired
    const response = await fetch(`${BACKEND_URL}/api/auth/session`, {
      method: "GET",
      // Forward the cookies so Flask can identify the user
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include",
    });

    // Get the response from Flask
    // Response will include: authenticated: true/false, user info, etc.
    const data = await response.json();

    // Return the session data to the browser
    // Frontend can use this to know if user is logged in
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    // If we can't reach the backend, assume user is not authenticated
    return NextResponse.json(
      {
        success: false,
        authenticated: false, // User is NOT logged in
        error: "Failed to connect to authentication server",
      },
      { status: 500 },
    );
  }
}
