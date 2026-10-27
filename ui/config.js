/* Generated to match repo-root `.env` — keep in sync with REALAI_API_BASE / PORT.
 * When Fusion UI is served by `python -m realai.api_server`, `/fusion-ui/config.js` is emitted
 * live and overrides this file. That live file leaves API_KEY blank on purpose:
 * the server never echoes REALAI_API_KEY. Put a key here only for a trusted local file.
 */
window.__REALAI_CONFIG__ = {
  BACKEND_BASE: 'http://127.0.0.1:8001',
  API_KEY: 'local',
  PORT: 8001,
};
