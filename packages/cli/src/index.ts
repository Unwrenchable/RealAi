#!/usr/bin/env node
import { Command } from "commander";
import { loginCommand } from "./commands/login";
import { whoamiCommand } from "./commands/whoami";
import { modelsListCommand } from "./commands/models";
import { chatCommand } from "./commands/chat";

const program = new Command();

program
  .name("realai")
  .description("RealAI CLI — interact with RealAI from your terminal")
  .version("0.1.0");

program
  .command("login")
  .description("Authenticate with an AI provider")
  .option("-p, --provider <provider>", "AI provider name")
  .action(async (options: { provider?: string }) => {
    await loginCommand(options);
  });

program
  .command("whoami")
  .description("Show current authentication details")
  .action(async () => {
    await whoamiCommand();
  });

const modelsCmd = program.command("models").description("Model management commands");

modelsCmd
  .command("list")
  .description("List available models")
  .action(async () => {
    await modelsListCommand();
  });

program
  .command("chat")
  .description("Start an interactive chat session")
  .option("-m, --model <model>", "Model to use")
  .option("-p, --provider <provider>", "AI provider")
  .option("-s, --system <prompt>", "System prompt")
  .action(async (options: { model?: string; provider?: string; system?: string }) => {
    await chatCommand(options);
  });

program.parse(process.argv);
