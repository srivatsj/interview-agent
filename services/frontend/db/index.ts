import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from 'pg'; 
import * as schema from "./schema";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  throw new Error("DATABASE_URL environment variable is not set");
}

// 3. Create a connection pool using the 'pg' package
const pool = new Pool({
  connectionString: connectionString,
});

// 4. Pass the Pool object to Drizzle (not a connection config object)
export const db = drizzle(pool, { schema: schema });