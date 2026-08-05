# Developer Onboarding

## 1. Install Dependencies

```bash
pnpm install
```

## 2. Start the Frontend

```bash
pnpm --filter realai-frontend dev
```

## 3. Start the Backend

```bash
python -m realai.api_server
```

## 4. Environment Variables

Copy `.env.example` to `.env` and update the values you need.

## 5. Workspace Layout

- Apps live in top-level folders such as `realai-frontend`.
- Shared code lives in `realai-core` and `realai-core/ui`.
- Providers live in `providers/`.
- Models live in `models/`.

## 6. Submitting Work

Run:

```bash
pnpm lint
pnpm typecheck
pnpm build
python3 test_realai.py
```