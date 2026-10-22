import { execFileSync } from "node:child_process";
import { MongoClient } from "mongodb";
import { ADMIN_EMAIL, ADMIN_PASSWORD, MONGO_URL } from "./environment";

/** Create the administrator of the run, the way scripts do, in an otherwise empty `users`. */
export default async function globalSetup() {
  const client = new MongoClient(MONGO_URL);
  await client.db().collection("users").deleteMany({});
  await client.close();

  execFileSync(
    "uv",
    [
      "run",
      "--project",
      "..",
      "daily-trends-py",
      "create-admin",
      "--email",
      ADMIN_EMAIL,
      "--password-stdin",
    ],
    {
      input: `${ADMIN_PASSWORD}\n`,
      env: { ...process.env, ENV: "test", MONGO_URL },
      stdio: ["pipe", "inherit", "inherit"],
    },
  );
}
