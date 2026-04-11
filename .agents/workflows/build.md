---
description: Build and lint the full World Analyst stack
---

// turbo-all

## Steps

1. Install Python backend dependencies
```bash
cd api && pip install -r requirements.txt
```

2. Install Python pipeline dependencies
```bash
cd pipeline && pip install -r requirements.txt
```

3. Lint Python code
```bash
ruff check api/ pipeline/
```

4. Install frontend dependencies
```bash
cd frontend && npm install
```

5. Lint frontend code
```bash
cd frontend && npm run lint
```

6. Build frontend for production
```bash
cd frontend && npm run build
```
