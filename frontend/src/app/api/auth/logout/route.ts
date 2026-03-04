import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ success: true });

  // Clear the httpOnly cookie
  response.cookies.set("access_token", "", { path: "/", expires: new Date(0) });

  return response;
}
