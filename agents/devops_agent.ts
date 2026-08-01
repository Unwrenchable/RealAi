import { Agent, Task, shell, fs } from "../core";

export default class DevOpsAgent extends Agent {
  name = "devops";
  description = "Expert deployment & DevOps assistant for all projects (Goonforge/cookbook, Atomic Fizz, RealAI, Supreme Goggles, etc.). Handles local env setup, frontend/backend deploys, Render, Vercel, contract deployments (EVM Hardhat + Solana Anchor), env management, troubleshooting, and CI/CD with project-specific knowledge.";

  // Project knowledge (expand as needed)
  private projects: Record<string, any> = {
    goonforge: {
      name: "Goonforge (cookbook / tokenforge)",
      stack: "Turbo + pnpm monorepo, Next.js 15 frontend (Vercel), EVM Hardhat contracts (multiple flavors + new naming/DomainRegistry), Solana Anchor (burn-bridge), shared lib",
      localSetup: "pnpm install; cd contracts/evm && cp .env.example .env (set Alchemy, deployer key); pnpm build or turbo run build",
      vercel: "Root vercel.json (or frontend/); set envs for WalletConnect, RPCs, contract addresses; supports monorepo with root or frontend dir",
      render: "Typically for any backend services; node env, start command from package",
      contracts: "Hardhat for EVM (factories, templates like BondingCurve, new naming); Anchor for Solana. Deploy scripts in contracts/*/scripts",
      envKeys: ["NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID", "ALCHEMY keys per chain", "contract addresses (factory, naming)", "treasury", "PRIVATE_KEY for deploys"],
      notes: "After token launch, use Supreme Goggles tab for .fizz / custom domains. New naming contract in contracts/evm/contracts/naming/"
    },
    atomicfizz: {
      name: "Atomic Fizz (wasteland GPS game)",
      stack: "Next.js frontend (static + some), Node backend server (Express), complex secrets, Solana program (fizzcaps_onchain + fizz-fun logic), Redis, RealAI integration, radio/NPC assets",
      localSetup: "npm install; setup Redis; fill .env with GAME_VAULT_SECRET, GPS_SECRET, VOUCHER_SECRET, XP_SECRET, SERVER_SECRET_KEY, CAPS_MINT, TREASURY, SOLANA_RPC, etc. Many base58 secrets + HF/xAI/R2 keys optional",
      vercel: "Frontend static deploy; backend separate. vercel.json at root",
      render: "Primary for backend (node service). render.yaml exists with web + env groups. Use for api.atomicfizzcaps.xyz style",
      contracts: "Anchor program deploy (update Anchor.toml mainnet ID after deploy). Fizz-fun is mostly offchain curve + onchain token creation",
      envKeys: ["ADMIN_PASSWORD", "GAME_VAULT_SECRET", "GPS_SECRET", "VOUCHER_SECRET", "XP_SECRET", "SERVER_SECRET_KEY", "CAPS_MINT", "TREASURY_WALLET", "REDIS_URL", "SOLANA_RPC (mainnet-beta)", "HELIUS_API_KEY", "XAI_API_KEY", "R2_*", "HF_API_KEY", "OPENAI_API_KEY for RealAI cloud"],
      notes: "Mainnet prep: use .env.mainnet, reliable RPC (Helius recommended), lock ADMIN_WALLETS. RealAi for NPCs, radio DJ voice (TTS wired). Separate from Goonforge."
    },
    realai: {
      name: "RealAI (your AI framework)",
      stack: "Python core + FastAPI-like server, local llama.cpp/vLLM, Next.js frontend parts, agents (including this devops one), Docker, plugins",
      localSetup: "pip install -e . or requirements; setup models (llama local or providers); export REALAI_*_API_KEY; python realai_local_server.py or main.py",
      vercel: "For any TS/Next parts (apps/frontend, src/); vercel.json present",
      render: "render.yaml for services (api, etc.); supports GPU via docker-compose or render GPU plans",
      contracts: "Web3 tools built-in (evm + solana backends in core)",
      envKeys: ["REALAI_OPENAI_API_KEY", "REALAI_ANTHROPIC...", "xAI/Grok, Gemini, etc.", "model paths for local", "server host/port"],
      notes: "Strong local + cloud provider routing. Use for helping generate more deployment agents/prompts. Has its own DEPLOYMENT.md"
    },
    supreme_goggles: {
      name: "Supreme Goggles (now integrated into Goonforge as naming)",
      stack: "Next.js naming dApp (domain search/register with any TLD), EVM DomainRegistry.sol (lifetime ownership), Solana program, multi-chain",
      localSetup: "Similar to goonforge frontend; WalletConnect key required",
      vercel: "Deploy as standalone or integrated in Goonforge frontend",
      render: "Less common (mostly client + onchain)",
      contracts: "DomainRegistry (ported to Goonforge contracts/evm/contracts/naming/). Deploy per chain, set treasury/fee",
      envKeys: ["NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID", "contract addresses per chain", "SOLANA_CONTRACT_ADDRESS", "PAYMENT addresses"],
      notes: "Integrated as /goggles tab in Goonforge. Use for .fizz domains post-launch. Original repo has rich docs and full standalone UI."
    }
  };

  async run(task: Task) {
    const input = task.input;
    const q = input.toLowerCase();

    // Detect project
    const projectKey = this.detectProject(input);
    const project = this.projects[projectKey] || this.projects.goonforge;

    // 1. Full project deployment wizard / checklist
    if (q.includes("setup") || q.includes("local") || q.includes("env") || q.includes("wizard") || q.includes("checklist")) {
      return this.deploymentWizard(projectKey, project, input);
    }

    // 2. Specific platform deploys
    if (q.includes("vercel") || q.includes("frontend deploy")) {
      return this.vercelDeploy(project, input);
    }
    if (q.includes("render")) {
      return this.renderDeploy(project, input);
    }

    // 3. Contract / onchain deploys (EVM + Solana)
    if (q.includes("contract") || q.includes("deploy") && (q.includes("evm") || q.includes("solana") || q.includes("anchor") || q.includes("hardhat") || q.includes("naming") || q.includes("goggles"))) {
      return this.contractDeploy(project, input);
    }

    // 4. General deploy
    if (q.includes("deploy")) {
      return this.generalDeploy(project, input);
    }

    // 5. Logs / monitoring
    if (q.includes("log") || q.includes("monitor") || q.includes("watch")) {
      return this.logsOrMonitor(project, input);
    }

    // 6. Fix / troubleshoot
    if (q.includes("fix") || q.includes("troubleshoot") || q.includes("error") || q.includes("fail")) {
      return this.troubleshoot(project, input);
    }

    // 7. Generate configs / templates
    if (q.includes("config") || q.includes("template") || q.includes("generate") || q.includes("render.yaml") || q.includes("vercel.json")) {
      return this.generateConfigs(project, input);
    }

    // Default: full guidance
    return this.fullGuidance(project, input);
  }

  detectProject(input: string): string {
    const i = input.toLowerCase();
    if (i.includes("goon") || i.includes("cookbook") || i.includes("tokenforge") || i.includes("fizz")) return "goonforge";
    if (i.includes("atomic") || i.includes("fizzcaps") || i.includes("wasteland") || i.includes("gps")) return "atomicfizz";
    if (i.includes("realai") || i.includes("real ai")) return "realai";
    if (i.includes("goggle") || i.includes("supreme") || i.includes("naming") || i.includes("domain")) return "supreme_goggles";
    return "goonforge"; // default to current main project
  }

  // =====================
  // DEPLOYMENT WIZARD
  // =====================
  async deploymentWizard(projectKey: string, project: any, input: string) {
    const target = input.toLowerCase().includes("vercel") ? "vercel" : 
                   input.toLowerCase().includes("render") ? "render" : 
                   input.toLowerCase().includes("local") ? "local" : "full";

    let guide = `# ${project.name} Deployment Wizard (${target.toUpperCase()})\n\n`;

    if (target === "local" || target === "full") {
      guide += `## 1. Local Environment Setup (easiest first run)\n\n`;
      guide += `**Commands:**\n\`\`\`bash\n${project.localSetup}\n\`\`\`\n\n`;
      guide += `**Critical .env keys** (copy from .env.example and fill):\n${project.envKeys.map((k: string) => `- ${k}`).join("\n")}\n\n`;
      guide += `**Tips:** Use direnv or a .envrc for secrets. For Solana parts: install solana-cli + anchor. Redis required for production-like local (Atomic/RealAI).\n\n`;
    }

    if (target === "vercel" || target === "full") {
      guide += this.vercelSection(project);
    }

    if (target === "render" || target === "full") {
      guide += this.renderSection(project);
    }

    guide += `\n## Contract / On-Chain Steps\n${this.contractSection(project)}\n`;

    guide += `\n**Next step:** Tell me exactly what you want (e.g. "setup local for goonforge with solana", "prepare vercel for cookbook frontend including goggles naming", "full render backend for atomic fizz mainnet", "deploy DomainRegistry to Polygon"). I can generate exact commands, full config files, or diagnose errors.`;

    return guide;
  }

  // Load additional structured knowledge if the runtime supports it (RAG / include the md)
  // The file agents/deployment-guide.md contains the full project-specific wizard knowledge.
  // In practice the surrounding RealAI agent system can feed it to you.

  vercelSection(project: any) {
    return `
## Vercel (Frontend / Static + some serverless)
- Install Vercel CLI: \`npm i -g vercel\`
- From project root (or frontend/ for monorepos like Goonforge): \`vercel\`
- Link to your Goonforge / AtomicFizz / RealAI project
- **Important env vars** (add via Vercel dashboard or \`vercel env add\`):
${project.envKeys.filter((k:string) => k.includes("NEXT_PUBLIC") || k.includes("PUBLIC")).map((k:string)=>`  - ${k}`).join("\n")}
- For monorepos (cookbook): Set "Root Directory" to \`frontend\` or configure in turbo + vercel.json
- Build command usually handled by next.config / turbo. Add \`NEXT_PUBLIC_* \` for client.
- After deploy: \`vercel --prod\`
- Common: Set \`NEXT_PUBLIC_USE_PRODUCTION_MODE=true\` where relevant (like goggles).
`;
  }

  renderSection(project: any) {
    return `
## Render (Backend services, often Node/Python APIs)
- Connect GitHub repo in Render dashboard
- Create "Web Service" (or Background Worker)
- **Build Command:** \`npm install\` or \`pnpm install\` or \`pip install -r requirements.txt\`
- **Start Command:** \`npm start\` or \`python realai_local_server.py\` or your server entry
- Use **Environment Groups** in Render for shared secrets across services
- Key envs: REDIS_URL (for prod), all the secret keys from above, \`NODE_ENV=production\`, \`PORT\` (Render sets it)
- For Atomic Fizz backend or RealAI API: often needs Redis addon on Render.
- Auto-deploy on push (can toggle per service).
- For GPU / heavy local models: may need custom Docker or external (RunPod, etc.).
`;
  }

  contractSection(project: any) {
    if (projectKeyForContracts(project) === "goonforge" || project.name.includes("Goonforge")) {
      return `
**EVM (Hardhat - factories, templates, new DomainRegistry for Goggles):**
cd contracts/evm
cp .env.example .env   # Alchemy keys + PRIVATE_KEY (deployer with funds) + TREASURY
npx hardhat compile
npx hardhat run scripts/deploy.ts --network polygon   # or mumbai, base, etc.
npx hardhat verify --network polygon <deployed-address>

**Solana (Anchor - burn bridge etc.):**
cd contracts/solana
anchor build
anchor deploy --provider.cluster devnet   # or mainnet-beta (update Anchor.toml program ID)
Use the burn-bridge for cross-chain from Solana launches.

**Naming (Supreme Goggles DomainRegistry):**
Deploy the one in contracts/evm/contracts/naming/ . After deploy, update Goonforge chain config or env so the GogglesPanel can call registerDomain.
`;
    }
    return `
**General contract deploy:** Use the project's scripts/ (Hardhat or Anchor). Update program IDs / contract addresses in frontend lib/chains.ts or env. Always verify on explorers. Test on devnet/testnet first.
`;
  }

  // =====================
  // Other helpers (expanded from original)
  // =====================

  async vercelDeploy(project: any, input: string) {
    return `Vercel deploy for ${project.name}:\n\n` + this.vercelSection(project) + 
           `\n\nRun in terminal or ask me to generate a full vercel.json tailored to this project + the new features (goggles, fizz, etc.).`;
  }

  async renderDeploy(project: any, input: string) {
    return `Render setup for ${project.name}:\n\n` + this.renderSection(project) +
           `\n\nI can output a complete render.yaml for your backend + any workers.`;
  }

  async generalDeploy(project: any, input: string) {
    return this.deploymentWizard(this.detectProject(input), project, input + " full");
  }

  async logsOrMonitor(project: any, input: string) {
    const svc = this.resolveServiceSmart(input, project);
    return `For ${project.name} / ${svc}:\n- Vercel: vercel logs <project> --since 1h\n- Render: render logs ${svc} --tail 200\n\nAsk for "stream logs" or "watch deploys" and I'll start monitoring logic if running in a context that supports it.`;
  }

  async troubleshoot(project: any, input: string) {
    return `Troubleshooting ${project.name}:\n\nCommon issues & fixes:\n- Missing env: compare against the critical keys listed above.\n- Vercel build fail: check monorepo root dir setting + turbo pipeline.\n- Contract deploy: insufficient funds, wrong network in .env or hardhat.config, verify API keys.\n- Render crash: Redis not connected, secret too long or malformed base58.\n- Solana: run \`anchor build\` locally first; check IDL paths.\n\nPaste the exact error and I'll give a precise fix + regenerated config if needed.`;
  }

  async generateConfigs(project: any, input: string) {
    let out = `Generated configs for ${project.name}\n\n`;
    out += `=== render.yaml (example for backend) ===\n${this.makeRenderYaml(project)}\n\n`;
    out += `=== vercel.json (monorepo friendly) ===\n${this.makeVercelJson(project)}\n\n`;
    out += `Ask me to customize further (e.g. "add goggles naming service" or "atomic fizz with redis").`;
    return out;
  }

  async fullGuidance(project: any, input: string) {
    return this.deploymentWizard(this.detectProject(input), project, "full checklist");
  }

  resolveServiceSmart(q: string, project: any) {
    // smarter version of original
    if (q.includes("front") || q.includes("ui") || q.includes("next") || q.includes("vercel")) return "frontend";
    if (q.includes("back") || q.includes("api") || q.includes("server") || q.includes("render")) return "backend";
    if (q.includes("contract") || q.includes("solana") || q.includes("evm")) return "contracts";
    return project.name.toLowerCase().includes("goon") ? "frontend" : "backend";
  }

  makeRenderYaml(project: any) {
    return `services:
  - type: web
    name: ${project.name.toLowerCase().replace(/\s+/g,'-')}-api
    env: node   # or python
    buildCommand: pnpm install   # or pip install -r requirements.txt
    startCommand: npm run start
    autoDeploy: true
    envVars:
      - key: NODE_ENV
        value: production
      # add all critical keys from the project list above (use Render Env Groups for secrets)`;
  }

  makeVercelJson(project: any) {
    const isMonorepo = project.name.toLowerCase().includes("goon") || project.name.toLowerCase().includes("cookbook");
    return JSON.stringify({
      "version": 2,
      "builds": isMonorepo ? undefined : [{ "src": "package.json", "use": "@vercel/node" }],
      "framework": "nextjs",
      ...(isMonorepo && { "rootDirectory": "frontend" }),
      "env": {}
    }, null, 2);
  }

  private projectKeyForContracts(p: any) { return p.name.includes("Goonforge") ? "goonforge" : "other"; }
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
