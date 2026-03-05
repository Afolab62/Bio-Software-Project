// Next.js API Route: Registration endpoint
// This file handles new user registration on the server side
// Location: app/api/auth/register/route.ts

import { NextResponse } from "next/server";

// Get the backend URL from environment variables
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

// POST function: Handles POST requests to /api/auth/register
export async function POST(request: Request) {
  try {
    // Extract email and password from request body
    const { email, password } = await request.json();

    // Basic validation: Check if both fields are provided
    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: "Email and password are required" },
        { status: 400 }, // 400 = Bad Request
      );
    }

    // Validate email format using a regular expression (regex)
    // This checks for: something@something.something pattern
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { success: false, error: "Invalid email format" },
        { status: 400 },
      );
    }

    // Validate password strength
    // Require at least 6 characters (you can add more rules as needed)
    if (password.length < 6) {
      return NextResponse.json(
        { success: false, error: "Password must be at least 6 characters" },
        { status: 400 },
      );
    }

    // Forward the registration request to Flask backend
    // Flask will actually create the user in the database
    const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", // Sending JSON data
      },
      credentials: "include", // Include cookies
      body: JSON.stringify({ email, password }), // Send as JSON string
    });

    // Get the response from Flask
    const data = await response.json();

    // Get session cookies from Flask (automatically logs user in after registration)
    const cookies = response.headers.get("set-cookie");
    const nextResponse = NextResponse.json(data, { status: response.status });

    // Forward the session cookie to the user's browser
    // This logs them in automatically after successful registration
    if (cookies) {
      nextResponse.headers.set("Set-Cookie", cookies);
    }

    return nextResponse;
  } catch (error) {
    // Handle any errors during registration
    return NextResponse.json(
      { success: false, error: "Failed to connect to authentication server" },
      { status: 500 }, // 500 = Internal Server Error
    );
  }
}
