import { pgSchema } from "drizzle-orm/pg-core";

// Define PostgreSQL schema namespaces
export const auth = pgSchema("auth");
export const product = pgSchema("product");
export const adk = pgSchema("adk");
