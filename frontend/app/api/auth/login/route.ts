// Next.js API Route: Login endpoint
// This file handles login requests on the server side (not in the browser)
// Location: app/api/auth/login/route.ts (Next.js App Router convention)

import { NextResponse } from "next/server";

// Get the backend URL from environment variables (.env file)
// Falls back to localhost:8000 if not set
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// POST function: Next.js automatically calls this when someone makes a POST request to /api/auth/login
// This is a server-side function - it runs on your server, not in the user's browser
export async function POST(request: Request) {
  try {
    // Extract email and password from the request body
    // request.json() parses the incoming JSON data
    const { email, password } = await request.json();

    // Validation: Check if both fields are provided
    if (!email || !password) {
      // NextResponse.json() creates a JSON response to send back to the client
      // Status 400 = Bad Request (client error)
      return NextResponse.json(
        { success: false, error: "Email and password are required" },
        { status: 400 },
      );
    }

    // Forward the login request to the Flask backend server
    // fetch() makes an HTTP request to another server
    const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", // Tell server we're sending JSON
      },
      credentials: "include", // Important: Include cookies in the request
      body: JSON.stringify({ email, password }), // Convert JS object to JSON string
    });

    // Parse the JSON response from Flask backend
    const data = await response.json();

    // Get session cookies from Flask response (used to keep user logged in)
    // Cookies are stored in the "set-cookie" header
    const cookies = response.headers.get("set-cookie");

    // Create the response to send back to the browser
    const nextResponse = NextResponse.json(data, { status: response.status });

    // If Flask sent cookies, forward them to the user's browser
    // This allows the browser to store the session cookie
    if (cookies) {
      nextResponse.headers.set("Set-Cookie", cookies);
    }

    return nextResponse;
  } catch (error) {
    // If anything goes wrong (network error, server down, etc.)
    // Return a 500 error (Internal Server Error)
    return NextResponse.json(
      { success: false, error: "Failed to connect to authentication server" },
      { status: 500 },
    );
  }
}
