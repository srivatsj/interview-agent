import { pgTable, uuid, jsonb, timestamp } from "drizzle-orm/pg-core";
import { interviews } from "./interviews";

export const canvasState = pgTable("canvas_state", {
  id: uuid("id").defaultRandom().primaryKey(),
  interviewId: uuid("interview_id")
    .notNull()
    .references(() => interviews.id, { onDelete: "cascade" })
    .unique(),
  elements: jsonb("elements").notNull(),
  appState: jsonb("app_state"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
