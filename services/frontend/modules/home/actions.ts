"use server";

import { db } from "@/db";
import { sql } from "drizzle-orm";

export interface RecentInterview {
  id: string;
  role: string | null;
  level: string | null;
  status: string;
  createdAt: Date;
  completedAt: Date | null;
  company: string | null;
  interviewType: string | null;
}

export async function getRecentInterviews(): Promise<RecentInterview[]> {
  try {
    // Join with ADK sessions table to get metadata from session state
    // ADK sessions table is in public schema, interviews is in product schema
    const result = await db.execute<{
      id: string;
      role: string | null;
      level: string | null;
      status: string;
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
        i.created_at,
        i.completed_at,
        s.state->'routing_decision'->>'company' as company,
        s.state->'routing_decision'->>'interview_type' as interview_type
      FROM product.interviews i
      LEFT JOIN public.sessions s ON (s.state->>'interview_id')::uuid = i.id
      WHERE i.status = 'completed'
      ORDER BY i.completed_at DESC
      LIMIT 3
    `);

    const rows = Array.isArray(result) ? result : result.rows || [];

    return rows.map((row) => ({
      id: row.id,
      role: row.role,
      level: row.level,
      status: row.status,
      createdAt: row.created_at,
      completedAt: row.completed_at,
      company: row.company,
      interviewType: row.interview_type,
    }));
  } catch (error) {
    console.error("Failed to fetch recent interviews:", error);
    throw new Error("Failed to fetch recent interviews");
  }
}
