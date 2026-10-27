"""RealAI hive built on the canonical agentx engine.

Modules:
- converters: .agent.md front-matter and hive role JSON -> .agentx manifests
- registry:   one loader for every agent source (AgentManifestLoader + converters)
- teams:      team files (lead, members, ownership, handoffs) -> AgentGraph
- governance: safe/balanced/power profiles, capability guardian, approval + sandbox gate
- overmind:   hive lead (plan -> route -> execute -> summarize -> hive memory)
- playtest:   QA loop; findings go to the owning agent over the MessageBus
"""
