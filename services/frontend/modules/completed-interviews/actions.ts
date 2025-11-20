"use server";

import { db } from "@/db";
import { canvasState } from "@/db/schema";
import { eq, sql } from "drizzle-orm";

export interface CompletedInterview {
  id: string;
  role: string | null;
  level: string | null;
  status: string;
  videoUrl: string | null;
  durationSeconds: number | null;
  createdAt: Date;
  completedAt: Date | null;
  company: string | null;
  interviewType: string | null;
}

interface GetCompletedInterviewsParams {
  page?: number;
  pageSize?: number;
}

export async function getCompletedInterviews(
  params: GetCompletedInterviewsParams = {},
): Promise<CompletedInterview[]> {
  const { page = 1, pageSize = 20 } = params;
  const offset = (page - 1) * pageSize;

  try {
    // Join with ADK sessions table to get metadata from session state
    // ADK sessions table is in public schema, interviews is in product schema
    const result = await db.execute<{
      id: string;
      role: string | null;
      level: string | null;
      status: string;
      video_url: string | null;
      duration_seconds: number | null;
      created_at: Date;
      completed_at: Date | null;
      company: string | null;
      interview_type: string | null;
    }>(sql`
      SELECT
        i.id,
        i.role,
        i.level,
        i.status,
        i.video_url,
        i.duration_seconds,
        i.created_at,
        i.completed_at,
        s.state->'routing_decision'->>'company' as company,
        s.state->'routing_decision'->>'interview_type' as interview_type
      FROM product.interviews i
      LEFT JOIN public.sessions s ON (s.state->>'interview_id')::uuid = i.id
      WHERE i.status = 'completed'
      ORDER BY i.completed_at DESC
      LIMIT ${pageSize}
      OFFSET ${offset}
    `);

    const rows = Array.isArray(result) ? result : result.rows || [];

    return rows.map((row) => ({
      id: row.id,
      role: row.role,
      level: row.level,
      status: row.status,
      videoUrl: row.video_url,
      durationSeconds: row.duration_seconds,
      createdAt: row.created_at,
      completedAt: row.completed_at,
      company: row.company,
      interviewType: row.interview_type,
    }));
  } catch (error) {
    console.error("Failed to fetch completed interviews:", error);
    throw new Error("Failed to fetch completed interviews");
  }
}

export interface TranscriptionRow {
  event_id: string;
  session_id: string;
  user_id: string;
  timestamp: Date;
  author: string;
  content_text: string;
  role: string;
}

export interface InterviewDetail extends CompletedInterview {
  transcriptions: TranscriptionRow[];
  canvasState: {
    elements: unknown[];
    appState: Record<string, unknown>;
  } | null;
  payment: {
    amountCents: number;
    status: string;
    createdAt: Date;
  } | null;
}

export async function getInterviewById(
  interviewId: string,
  userId: string,
): Promise<InterviewDetail | null> {
  try {
    // Get interview data joined with ADK session for metadata
    // ADK sessions table is in public schema, interviews is in product schema
    const interviewResult = await db.execute<{
      id: string;
      role: string | null;
      level: string | null;
      status: string;
      video_url: string | null;
      duration_seconds: number | null;
      created_at: Date;
      completed_at: Date | null;
      company: string | null;
      interview_type: string | null;
    }>(sql`
      SELECT
        i.id,
        i.role,
        i.level,
        i.status,
        i.video_url,
        i.duration_seconds,
        i.created_at,
        i.completed_at,
        s.state->'routing_decision'->>'company' as company,
        s.state->'routing_decision'->>'interview_type' as interview_type
      FROM product.interviews i
      LEFT JOIN public.sessions s ON (s.state->>'interview_id')::uuid = i.id
      WHERE i.id = ${interviewId}
      LIMIT 1
    `);

    const interviewRows = Array.isArray(interviewResult)
      ? interviewResult
      : interviewResult.rows || [];

    if (interviewRows.length === 0) {
      return null;
    }

    const interviewData = interviewRows[0];
    const interview = {
      id: interviewData.id,
      role: interviewData.role,
      level: interviewData.level,
      status: interviewData.status,
      videoUrl: interviewData.video_url,
      durationSeconds: interviewData.duration_seconds,
      createdAt: interviewData.created_at,
      completedAt: interviewData.completed_at,
      company: interviewData.company,
      interviewType: interviewData.interview_type,
    };

    // Get canvas state
    const [canvas] = await db
      .select({
        elements: canvasState.elements,
        appState: canvasState.appState,
      })
      .from(canvasState)
      .where(eq(canvasState.interviewId, interviewId))
      .limit(1);

    // Get payment information
    let payment: { amountCents: number; status: string; createdAt: Date } | null = null;
    try {
      const paymentResult = await db.execute<{
        amount_cents: number;
        status: string;
        created_at: Date;
      }>(sql`
        SELECT
          amount_cents,
          status,
          created_at
        FROM product.ap2_transactions
        WHERE interview_id = ${interviewId}
        LIMIT 1
      `);

      const paymentRows = Array.isArray(paymentResult)
        ? paymentResult
        : paymentResult.rows || [];

      if (paymentRows.length > 0) {
        const paymentData = paymentRows[0];
        payment = {
          amountCents: paymentData.amount_cents,
          status: paymentData.status,
          createdAt: paymentData.created_at,
        };
      }
    } catch (error) {
      console.error("Failed to fetch payment information:", error);
      // Continue without payment info rather than failing
    }

    // Get transcriptions from ADK events table
    let transcriptions: TranscriptionRow[] = [];
    try {
      type RawEvent = {
        event_id: string;
        session_id: string;
        user_id: string;
        timestamp: Date;
        author: string;
        content: {
          input_transcription?: { text: string };
          output_transcription?: { text: string };
          parts?: Array<{ text?: string }>;
          role?: string;
        };
      };

      const result = await db.execute(sql`
        SELECT
          e.id as event_id,
          e.session_id,
          e.user_id,
          e.timestamp,
          e.author,
          e.content
        FROM events e
        INNER JOIN sessions s ON
          s.app_name = e.app_name
          AND s.user_id = e.user_id
          AND s.id = e.session_id
        WHERE
          s.state->>'interview_id' = ${interviewId}
          AND e.user_id = ${userId}
          AND e.content IS NOT NULL
        ORDER BY e.timestamp ASC
      `);

      const rawEvents = (Array.isArray(result) ? result : result.rows || []) as RawEvent[];

      // Extract text from the content JSONB
      const extractedTranscriptions = rawEvents
        .map((event: RawEvent) => {
          let content_text = null;
          let role = "unknown";

          if (event.content) {
            const content = event.content;

            // Check for input_transcription (user speech from Gemini)
            if (content.input_transcription?.text) {
              content_text = content.input_transcription.text;
              role = "user";
            }
            // Check for output_transcription (agent speech from Gemini)
            else if (content.output_transcription?.text) {
              content_text = content.output_transcription.text;
              role = "model";
            }
            // Check content.parts[].text (model text responses)
            else if (content.parts && Array.isArray(content.parts)) {
              const textPart = content.parts.find((p) => p.text);
              if (textPart) {
                content_text = textPart.text;
                role = content.role || "unknown";
              }
            }
          }

          if (content_text && content_text.trim()) {
            return {
              event_id: event.event_id,
              session_id: event.session_id,
              user_id: event.user_id,
              timestamp: event.timestamp,
              author: event.author,
              content_text,
              role,
            };
          }
          return null;
        })
        .filter((t): t is TranscriptionRow => t !== null);

      // Group consecutive messages from the same author
      const groupedTranscriptions: TranscriptionRow[] = [];
      for (const trans of extractedTranscriptions) {
        const lastGroup =
          groupedTranscriptions[groupedTranscriptions.length - 1];

        if (lastGroup && lastGroup.author === trans.author) {
          lastGroup.content_text += trans.content_text;
          lastGroup.timestamp = trans.timestamp;
        } else {
          groupedTranscriptions.push({ ...trans });
        }
      }

      transcriptions = groupedTranscriptions;
    } catch (error) {
      console.error("Failed to fetch transcriptions:", error);
      // Continue without transcriptions rather than failing
    }

    return {
      ...interview,
      transcriptions,
      canvasState: canvas
        ? {
            elements: (canvas.elements || []) as unknown[],
            appState: (canvas.appState || {}) as Record<string, unknown>,
          }
        : null,
      payment,
    };
  } catch (error) {
    console.error("Failed to fetch interview details:", error);
    throw new Error("Failed to fetch interview details");
  }
}
