import { fs, http } from "../core";
import DevOpsAgent from "../agents/devops_agent";

type AutopilotConfig = {
  repoPath: string;
  discordWebhook?: string;
};

export class Autopilot {
  private readonly devops: DevOpsAgent;
  private readonly config: AutopilotConfig;

  constructor(config: AutopilotConfig) {
    this.devops = new DevOpsAgent();
    this.config = config;
  }

  async start() {
    this.log("Autopilot started.");
    this.watchRepo();
  }

  private log(msg: string) {
    console.log(`[Autopilot] ${msg}`);
  }

  private async notify(message: string) {
    this.log(message);

    if (!this.config.discordWebhook) return;

    try {
      await http.post(this.config.discordWebhook, {
        content: `**RealAI Autopilot**\n${message}`,
      });
    } catch (e) {
      this.log(`Discord notify failed: ${String(e)}`);
    }
  }

  private watchRepo() {
    const path = this.config.repoPath;

    this.log(`Watching repo: ${path}`);

    fs.watch(path, async (_event, file) => {
      if (!file) return;

      const f = file.toString();
      if (!f.match(/\.(ts|tsx|js|jsx|json|toml|yaml|yml|env)$/)) return;

      this.log(`Change detected: ${f}`);

      // Decide what to deploy
      if (f.includes("frontend") || f.includes("next") || f.includes("vercel")) {
        await this.handleDeploy("frontend");
      } else if (f.includes("backend") || f.includes("api") || f.includes("render")) {
        await this.handleDeploy("backend");
      } else {
        // Default: backend only
        await this.handleDeploy("backend");
      }
    });
  }

  private async handleDeploy(target: "backend" | "frontend") {
    await this.notify(`Change detected -> deploying **${target}**...`);

    if (target === "backend") {
      const result = await this.devops.run({ input: "deploy backend" });
      await this.notify(`Backend deploy result:\n\`\`\`\n${result}\n\`\`\``);
      return;
    }

    if (target === "frontend") {
      const result = await this.devops.run({ input: "deploy frontend" });
      await this.notify(`Frontend deploy result:\n\`\`\`\n${result}\n\`\`\``);
    }
  }
}

export default Autopilot;
