import { NextRequest, NextResponse } from "next/server";
import { put } from "@vercel/blob";
import { db } from "@/db";
import { interviews } from "@/db/schema/interviews";
import { eq } from "drizzle-orm";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;

    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return NextResponse.json(
        { error: `Invalid interview ID format: ${id}` },
        { status: 400 },
      );
    }

    // Check if interview exists
    const existingInterview = await db
      .select({ id: interviews.id })
      .from(interviews)
      .where(eq(interviews.id, id))
      .limit(1);

    if (existingInterview.length === 0) {
      return NextResponse.json(
        { error: `Interview not found: ${id}` },
        { status: 404 },
      );
    }

    // Get form data
    const formData = await request.formData();
    const recording = formData.get("recording") as File;

    if (!recording) {
      return NextResponse.json(
        { error: "No recording file provided" },
        { status: 400 },
      );
    }

    console.log(
      `📤 Uploading recording for interview ${id} (${(recording.size / 1024 / 1024).toFixed(2)} MB)`,
    );

    // Upload to Vercel Blob
    const { url } = await put(`recordings/${id}.webm`, recording, {
      access: "public",
      addRandomSuffix: false,
    });

    console.log(`✅ Recording uploaded: ${url}`);

    // Update database
    await db
      .update(interviews)
      .set({
        videoUrl: url,
        status: "completed",
        completedAt: new Date(),
      })
      .where(eq(interviews.id, id));

    console.log(`✅ Database updated for interview ${id}`);

    return NextResponse.json({ url, interviewId: id });
  } catch (error) {
    console.error("Upload recording error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Upload failed" },
      { status: 500 },
    );
  }
}
