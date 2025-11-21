"use server";

import { db } from "@/db";
import { interviews, canvasState } from "@/db/schema";
import { eq } from "drizzle-orm";

export interface CreateInterviewInput {
  company?: string;
  role?: string;
  level?: string;
  type?: string;
}

export interface Interview {
  id: string;
  role: string | null;
  level: string | null;
  status: string;
  createdAt: Date;
}

export async function createInterview(
  input: CreateInterviewInput = {},
): Promise<Interview> {
  const { role, level } = input;

  try {
    const [interview] = await db
      .insert(interviews)
      .values({
        role: role || "Software Engineer",
        level: level || "Senior",
        status: "in_progress",
      })
      .returning();

    return {
      id: interview.id,
      role: interview.role,
      level: interview.level,
      status: interview.status,
      createdAt: interview.createdAt,
    };
  } catch (error) {
    console.error("Failed to create interview:", error);
    throw new Error("Failed to create interview");
  }
}

export async function validateInterviewExists(
  interviewId: string,
): Promise<boolean> {
  try {
    // Validate UUID format
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(interviewId)) {
      return false;
    }

    // Check if interview exists in database
    const result = await db
      .select({ id: interviews.id })
      .from(interviews)
      .where(eq(interviews.id, interviewId))
      .limit(1);

    return result.length > 0;
  } catch (error) {
    console.error("Failed to validate interview:", error);
    return false;
  }
}

export interface UpdateInterviewInput {
  interviewId: string;
  status?: string;
  videoUrl?: string;
  completedAt?: Date;
  durationSeconds?: number;
  canvasState?: {
    elements: unknown[];
    appState?: Record<string, unknown>;
  };
}

export async function updateInterview(params: UpdateInterviewInput) {
  const { interviewId, canvasState: canvas, ...updates } = params;

  try {
    // Update interview record
    if (Object.keys(updates).length > 0) {
      await db
        .update(interviews)
        .set(updates)
        .where(eq(interviews.id, interviewId));
    }

    // Store canvas state if provided
    if (canvas && (canvas.elements || canvas.appState)) {
      await db.insert(canvasState).values({
        interviewId,
        elements: canvas.elements || [],
        appState: canvas.appState || {},
      });
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to update interview:", error);
    throw new Error("Failed to update interview");
  }
}

export async function getInterviewWithCanvas(interviewId: string) {
  try {
    const [interview] = await db
      .select()
      .from(interviews)
      .where(eq(interviews.id, interviewId))
      .limit(1);

    if (!interview) {
      return null;
    }

    const [canvas] = await db
      .select()
      .from(canvasState)
      .where(eq(canvasState.interviewId, interviewId))
      .limit(1);

    return {
      ...interview,
      canvasState: canvas || null,
    };
  } catch (error) {
    console.error("Failed to get interview with canvas:", error);
    return null;
  }
}
