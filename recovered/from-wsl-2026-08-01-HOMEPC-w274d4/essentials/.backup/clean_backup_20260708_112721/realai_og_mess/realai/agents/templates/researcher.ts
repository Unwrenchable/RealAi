/**
 * Researcher Agent Template
 * Searches the web and synthesizes findings
 */

const researcherAgent = {
  name: "researcher",
  model: "realai-overseer",
  tools: ["web-search", "fetch-url", "summarize"],
  memory: null,
};

export default researcherAgent;
