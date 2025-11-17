import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "postgresql",
  schema: "./db/schema",
  out: "./drizzle",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  schemaFilter: ["auth", "product"], // Only manage frontend schemas, not "adk" (orchestrator)
  verbose: true,
  strict: true,
});