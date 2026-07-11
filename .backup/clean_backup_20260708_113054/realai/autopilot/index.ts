import Autopilot from "./autopilot";

const autopilot = new Autopilot({
  repoPath: "../", // adjust if needed
  // discordWebhook: "https://discord.com/api/webhooks/....",
});

autopilot.start();
