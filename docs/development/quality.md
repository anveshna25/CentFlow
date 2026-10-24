# CentFlow Development Quality Conventions

## 1. Overview

CentFlow adheres to structured engineering standards to ensure high maintainability, deterministic testability, code clarity, and architectural consistency across both the FastAPI backend and React frontend.

All contributions to CentFlow are automatically validated through continuous integration before they can be merged into `main`.

---

## 2. Backend Quality Standards

### Python Version Support
CentFlow backend services are written for **Python 3.11+** (supporting 3.11 and 3.12).

### Code Style & Structure
- **Type Annotations:** All functions, methods, parameters, and return values should be explicitly type-annotated (`int`, `str`, `Decimal`, `Optional[T]`, `Sequence[T]`, etc.).
- **Data Validation & Envelopes:** All external input parameters and API responses must be modeled with typed Pydantic models inheriting from `BaseSchema`, wrapped inside `ResponseEnvelope[T]`.
- **Error Handling:** Use domain-specific exceptions subclassing `CentFlowError` from `app.core.errors`. Never expose raw uncaught traceback errors to API consumers.

### Testing Conventions
- **Test Framework:** Unit tests use the standard Python `unittest` library and `unittest.IsolatedAsyncioTestCase` for asynchronous route and provider testing.
- **Deterministic Test Isolation:** Tests must not depend on live internet connectivity or external third-party market data feeds. Use `MockMarketDataProvider` or local mocks.
- **Execution Command:**
  ```bash
  cd backend
  python -m unittest discover -s tests -v
  ```
- **Test Structure:**
  - `backend/tests/test_domain_models.py`: Domain entity immutability and validations.
  - `backend/tests/test_market_data.py`: Provider abstractions, registry, and mock provider simulation.
  - `backend/tests/test_api_market_data.py`: API route contracts and response envelope validations.

---

## 3. Frontend Quality Standards

### Node.js Runtime
Frontend development requires **Node.js 20 LTS** or newer.

### Component Design & React Patterns
- **Atomic & Functional:** Components are strictly functional, styled with CentFlow's Vanilla CSS design system tokens (`var(--cf-...)`), and free of external UI bloat.
- **Hooks Compliance:** Adhere to React Hooks rules:
  - Do not call `setState` synchronously within effect bodies (`react-hooks/set-state-in-effect`).
  - Use cancellation tokens (`let isCancelled = false`) in asynchronous data-fetching effects to prevent memory leaks and unmounted component updates.
- **Unique Test Identifiers:** Interactive and structural elements must include clear, descriptive DOM IDs (e.g. `id="cf-markets-page"`, `id="filter-tab-crypto"`).

### Static Analysis & Linter
All JavaScript and JSX files must pass ESLint with zero errors and zero warnings:
```bash
cd frontend
npm run lint
```

### Production Build Validation
Prior to PR submission, the Vite production bundle must compile without bundling errors:
```bash
cd frontend
npm run build
```

---

## 4. Automated Continuous Integration (CI)

CentFlow uses GitHub Actions configured in `.github/workflows/ci.yml`. The workflow triggers on all `push` events to `main` and all `pull_request` events targeting `main`.

### Workflow Jobs
1. **Backend Tests:**
   - Runs on a matrix of Python `3.11` and `3.12`.
   - Caches pip packages based on `backend/requirements.txt`.
   - Executes the complete unit test suite.
2. **Frontend Lint & Build:**
   - Runs on Node.js `20`.
   - Caches npm packages based on `frontend/package-lock.json`.
   - Runs `npm ci`, `npm run lint`, and `npm run build`.

Both jobs must report success for a pull request to be considered ready to merge.

---

## 5. Pre-PR Verification Checklist

Before pushing commits and requesting code review, verify the following checklist locally:

1. **Backend Tests Pass:**
   ```bash
   cd backend
   python -m unittest discover -s tests -v
   ```
2. **Frontend Linter Passes:**
   ```bash
   cd frontend
   npm run lint
   ```
3. **Frontend Production Build Passes:**
   ```bash
   cd frontend
   npm run build
   ```
4. **Clean Git Diff:**
   ```bash
   git diff --check
   ```
5. **Privacy & Environment Audit:**
   - Verify no `.env` files or credentials are staged.
   - Verify all documentation links use relative repository paths rather than absolute local workstation paths.
   - Confirm zero occurrences of personal machine usernames.
