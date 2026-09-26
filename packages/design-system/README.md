# @realai/design-system

In-tree RealAI UI package (ported as prebuilt `dist/` + pure `tokens.cjs`).

## Tokens (Tailwind)

```js
// frontend/tailwind.config.js
const { tailwindExtension } = require("@realai/design-system/tokens");
module.exports = {
  theme: { extend: { ...tailwindExtension, /* local overrides */ } },
};
```

## React components

```tsx
import { Button, Card, ChatBubble, colors } from "@realai/design-system";
```

Requires React 18+ peer dependency (provided by `frontend/`).
