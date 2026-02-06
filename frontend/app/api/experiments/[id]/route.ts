import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;

    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/experiments/${id}`, {
      method: "GET",
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include",
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to server" },
      { status: 500 },
    );
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const body = await request.json();

    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/experiments/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      },
      credentials: "include",
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to server" },
      { status: 500 },
    );
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;

    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/experiments/${id}`, {
      method: "DELETE",
      headers: cookieHeader ? { Cookie: cookieHeader } : {},
      credentials: "include",
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to server" },
      { status: 500 },
    );
  }
}
