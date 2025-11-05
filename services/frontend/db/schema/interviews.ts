import { pgTable, uuid, text, timestamp, integer } from "drizzle-orm/pg-core";

export const interviews = pgTable("interviews", {
  id: uuid("id").defaultRandom().primaryKey(),

  // metadata
  role: text("role"),           // ex: "Backend Engineer"
  level: text("level"),         // ex: "Senior"
  status: text("status").notNull().default("in_progress"), 

  createdAt: timestamp("created_at").defaultNow().notNull(),
  completedAt: timestamp("completed_at"),
});
