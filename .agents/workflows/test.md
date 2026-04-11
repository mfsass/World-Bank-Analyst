---
description: Run all tests across the World Analyst stack
---

// turbo-all

## Steps

1. Run backend API tests
```bash
cd api && python -m pytest tests/ -v
```

2. Run pipeline tests
```bash
cd pipeline && python -m pytest tests/ -v
```

3. Run frontend tests (if configured)
```bash
cd frontend && npm test -- --passWithNoTests
```
