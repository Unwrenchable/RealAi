import * as vscode from 'vscode';
import { RealAIClient } from './realaiClient';
import { buildStageBrief, StageBrief } from './stageContext';

export interface StackSnapshot {
  ok: boolean;
  baseUrl: string;
  hiveOk: boolean;
  vulkanOk: boolean;
  service?: string;
  hiveAgents: string[];
  hiveAgentCount: number;
  toolsCount: number;
  agentsCount: number;
  capabilitiesCount: number;
  selfHealEnabled?: boolean;
  promoteActionable?: number;
  abilityCount?: number;
  loraCount?: number;
  voiceOk: boolean;
  voiceUrl: string;
  voiceBackend?: string;
  voiceLabOk?: boolean;
  stage: StageBrief;
  errors: string[];
  summaryLine: string;
  collectedAt: string;
}

export async function collectStackSnapshot(client: RealAIClient): Promise<StackSnapshot> {
  const stage = buildStageBrief();
  const errors: string[] = [];
  let hiveOk = false;
  let vulkanOk = false;
  let service: string | undefined;
  let hiveAgents: string[] = [];
  let hiveAgentCount = 0;
  let toolsCount = 0;
  let agentsCount = 0;
  let capabilitiesCount = 0;
  let selfHealEnabled: boolean | undefined;
  let promoteActionable: number | undefined;
  let abilityCount: number | undefined;
  let loraCount: number | undefined;
  let voiceOk = false;
  let voiceLabOk = false;
  let voiceBackend: string | undefined;
  let voiceUrl =
    vscode.workspace.getConfiguration('realai').get<string>('voiceUrl') ||
    'http://127.0.0.1:8890';

  try {
    const health = await client.getHealth();
    hiveOk = String(health.status || '').toLowerCase() === 'ok' || !!(health as any).service;
    service = (health as any).service || health.status;
    vulkanOk = !!(health as any).vulkan?.ok;
  } catch (e: any) {
    errors.push(`health: ${e?.message || e}`);
  }

  try {
    const hive = await client.getHive();
    hiveAgents = hive?.agents?.present || [];
    hiveAgentCount = hive?.agents?.count || hiveAgents.length;
  } catch (e: any) {
    errors.push(`hive: ${e?.message || e}`);
  }

  try {
    const tools = await client.listTools();
    toolsCount = Array.isArray(tools?.tools) ? tools.tools.length : 0;
  } catch (e: any) {
    errors.push(`tools: ${e?.message || e}`);
  }

  try {
    const agents = await client.listAgents();
    agentsCount = Array.isArray(agents?.data) ? agents.data.length : 0;
  } catch (e: any) {
    errors.push(`agents: ${e?.message || e}`);
  }

  try {
    const caps = await client.getCapabilities();
    const list = caps?.capabilities || caps;
    capabilitiesCount = Array.isArray(list) ? list.length : 0;
  } catch (e: any) {
    errors.push(`capabilities: ${e?.message || e}`);
  }

  try {
    const heal = await client.getSelfHealStatus();
    selfHealEnabled = !!heal?.enabled;
    promoteActionable = heal?.promote_actionable;
    abilityCount =
      heal?.ability_coverage?.ability_count ??
      (Array.isArray(heal?.abilities) ? heal.abilities.length : undefined);
  } catch (e: any) {
    errors.push(`self-heal: ${e?.message || e}`);
  }

  try {
    const lora = await client.getLora();
    loraCount = lora?.count ?? (Array.isArray(lora?.data) ? lora.data.length : undefined);
  } catch (e: any) {
    errors.push(`lora: ${e?.message || e}`);
  }

  try {
    voiceLabOk = await client.probeUrl(`${voiceUrl.replace(/\/$/, '')}/health`);
    if (voiceLabOk) {
      voiceOk = true;
      voiceBackend = 'voice-lab';
    }
  } catch {
    voiceLabOk = false;
  }
  // Voice Lab :8890 preferred. Hive in-process Kokoro (or SAPI) still counts as voice OK.
  if (!voiceOk && hiveOk) {
    try {
      const vh = await client.executeTool('voice_health', {});
      const inner = (vh as any)?.result || vh || {};
      const models = inner.models_present || {};
      if (inner.ok || models.kokoro || models.fish || models.xtts) {
        voiceOk = true;
        voiceBackend = String(inner.default_backend || 'hive-tts');
        voiceUrl = `${client.getBaseUrl().replace(/\/$/, '')} (hive ${voiceBackend})`;
      }
    } catch (e: any) {
      errors.push(`voice: ${e?.message || e}`);
    }
  }

  const ok = hiveOk;
  const summaryLine = [
    ok ? 'Hive OK' : 'Hive DOWN',
    vulkanOk ? 'Vulkan OK' : 'Vulkan ?',
    voiceOk ? `Voice OK${voiceBackend ? ' (' + voiceBackend + ')' : ''}` : 'Voice off',
    `tools ${toolsCount}`,
    `agents ${agentsCount}`,
    `caps ${capabilitiesCount}`,
    stage.summaryLine,
  ].join(' · ');

  return {
    ok,
    baseUrl: client.getBaseUrl(),
    hiveOk,
    vulkanOk,
    service,
    hiveAgents,
    hiveAgentCount,
    toolsCount,
    agentsCount,
    capabilitiesCount,
    selfHealEnabled,
    promoteActionable,
    abilityCount,
    loraCount,
    voiceOk,
    voiceUrl,
    voiceBackend,
    voiceLabOk,
    stage,
    errors,
    summaryLine,
    collectedAt: new Date().toISOString(),
  };
}
