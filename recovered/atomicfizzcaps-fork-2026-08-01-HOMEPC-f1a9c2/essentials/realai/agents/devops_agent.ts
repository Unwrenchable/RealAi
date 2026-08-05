import { Agent, Task, shell, fs } from "../core";

export default class DevOpsAgent extends Agent {
  name = "devops";
  description = "Autonomous DevOps operator for Render, Vercel, and GitHub.";

  async run(task: Task) {
    const q = task.input.toLowerCase();

    // 1. Repo watcher
    if (q.includes("watch") || q.includes("monitor")) {
      return this.watchRepo();
    }

    // 2. Deploy commands
    if (q.includes("deploy")) {
      return this.deploy(q);
    }

    // 3. Environment sync
    if (q.includes("env")) {
      return this.syncEnv(q);
    }

    // 4. Logs
    if (q.includes("logs")) {
      return this.logs(q);
    }

    // 5. Fix configs
    if (q.includes("fix")) {
      return this.fixConfigs();
    }

    return "DevOpsAgent: I understood the request but no action matched.";
  }

  // -----------------------------
  // WATCH REPO FOR CHANGES
  // -----------------------------
  async watchRepo() {
    this.say("Watching repo for changes...");

    fs.watch("../", async (event, file) => {
      if (typeof file === "string" && file.endsWith(".ts")) {
        this.say(`Detected ${event} in ${file}`);
        await this.deploy("backend");
      }
    });

    return "DevOpsAgent: Repo watcher active.";
  }

  // -----------------------------
  // DEPLOY LOGIC
  // -----------------------------
  async deploy(query: string) {
    const service = this.resolveService(query);

    if (!service) return "DevOpsAgent: Could not resolve service.";

    this.say(`Deploying ${service}...`);

    if (service.includes("backend")) {
      return shell(`render deploy ${service}`);
    }

    if (service.includes("frontend")) {
      return shell("vercel --prod --yes --cwd ~/atomic-fizz-caps-frontend");
    }

    return "DevOpsAgent: Deploy complete.";
  }

  // -----------------------------
  // ENV SYNC
  // -----------------------------
  async syncEnv(query: string) {
    const service = this.resolveService(query) ?? "atomic-fizz-caps-backend";

    this.say(`Syncing env for ${service}...`);

    const renderEnv = await shell(`render env:get ${service}`);
    const vercelEnv = await shell("vercel env pull .env.local");

    return `
Render ENV:
${renderEnv}

Vercel ENV:
${vercelEnv}

DevOpsAgent: Env sync complete.
`;
  }

  // -----------------------------
  // LOGS
  // -----------------------------
  async logs(query: string) {
    const service = this.resolveService(query) ?? "atomic-fizz-caps-backend";

    this.say(`Fetching logs for ${service}...`);

    if (service.includes("backend")) {
      return shell(`render logs ${service} --tail 200`);
    }

    if (service.includes("frontend")) {
      return shell("vercel logs atomic-fizz-caps-frontend --since 1h");
    }

    return "DevOpsAgent: Logs complete.";
  }

  // -----------------------------
  // FIX CONFIGS
  // -----------------------------
  async fixConfigs() {
    this.say("Fixing Render + Vercel configs...");

    await fs.write("render.yaml", this.templates.render());
    await fs.write("vercel.json", this.templates.vercel());

    return "DevOpsAgent: Configs patched.";
  }

  // -----------------------------
  // SERVICE RESOLVER
  // -----------------------------
  resolveService(q: string) {
    q = q.toLowerCase();

    if (q.includes("fizzcaps") || q.includes("caps") || q.includes("atomic"))
      return "atomic-fizz-caps-backend";

    if (q.includes("realai") || q.includes("core") || q.includes("brain"))
      return "realai-core";

    if (q.includes("front") || q.includes("ui") || q.includes("web"))
      return "atomic-fizz-caps-frontend";

    if (q.includes("api") || q.includes("server"))
      return "backend-api";

    return null;
  }

  // -----------------------------
  // CONFIG TEMPLATES
  // -----------------------------
  templates = {
    render: () => `
services:
  - type: web
    name: atomic-fizz-caps-backend
    env: node
    buildCommand: npm install
    startCommand: npm start
    autoDeploy: true
`,
    vercel: () => `
{
  "version": 2,
  "builds": [{ "src": "next.config.js", "use": "@vercel/next" }],
  "env": {}
}
`,
  };
}
