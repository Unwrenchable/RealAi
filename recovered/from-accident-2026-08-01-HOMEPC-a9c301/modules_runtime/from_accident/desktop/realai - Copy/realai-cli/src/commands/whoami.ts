import { readConfig, maskApiKey } from "../config";

export async function whoamiCommand(): Promise<void> {
  const { default: chalk } = await import("chalk");

  const config = readConfig();

  if (!config.apiKey && !config.provider) {
    console.log(chalk.yellow("Not logged in. Run `realai login` to authenticate."));
    return;
  }

  console.log(chalk.bold.cyan("\n🤖 RealAI Identity\n"));

  if (config.provider) {
    console.log(`  ${chalk.dim("Provider:")} ${chalk.white(config.provider)}`);
  }
  if (config.model) {
    console.log(`  ${chalk.dim("Model:   ")} ${chalk.white(config.model)}`);
  }
  if (config.apiKey) {
    const masked = maskApiKey(config.apiKey);
    console.log(`  ${chalk.dim("API Key: ")} ${chalk.white(masked)}`);
  }
  if (config.baseUrl) {
    console.log(`  ${chalk.dim("Base URL:")} ${chalk.white(config.baseUrl)}`);
  }
  console.log();
}
