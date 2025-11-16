import { uuid, text, timestamp, integer } from "drizzle-orm/pg-core";
import { product } from "./namespaces";

export const interviews = product.table("interviews", {
  id: uuid("id").defaultRandom().primaryKey(),

  // metadata
  role: text("role"),           // ex: "Backend Engineer"
  level: text("level"),         // ex: "Senior"
  status: text("status").notNull().default("in_progress"),

  // recordings
  videoUrl: text("video_url"),  // Full screen recording (canvas + webcam + UI)
  durationSeconds: integer("duration_seconds"), // Interview duration

  createdAt: timestamp("created_at").defaultNow().notNull(),
  completedAt: timestamp("completed_at"),
});
