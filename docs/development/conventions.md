# CentFlow Development Conventions

## 1. Purpose

This document defines the initial development conventions for CentFlow.

These conventions are intentionally lightweight and may evolve as the project grows.

## 2. Repository Structure

The repository separates major application responsibilities:

```text
backend/      Server-side Python application
frontend/     React frontend application
docs/         Project documentation
```

Additional directories should be introduced only when they represent a clear project responsibility.

## 3. Branching

Development work should be performed on feature branches.

Branch names should clearly describe the work being performed.

Examples:

```text
feature/project-documentation
feature/market-data
feature/asset-analysis
fix/api-validation
```

## 4. Pull Requests

Changes should be submitted through pull requests rather than directly committing development work to `main`.

Pull requests should clearly communicate:

- what changed
- why it changed
- how it was verified

## 5. Commits

Commit messages should describe the purpose of the change.

Examples:

```text
feat: add market data service
fix: handle invalid asset symbol
docs: establish project documentation
chore: update backend dependencies
```

## 6. Environment Configuration

Environment-specific configuration should not be committed when it contains secrets or machine-specific values.

The repository should provide `.env.example` files where environment variables need to be documented.

Actual `.env` files should remain excluded from version control.

## 7. Dependencies

Dependencies should be explicitly declared in the appropriate project dependency files.

Backend Python dependencies are maintained in:

```text
backend/requirements.txt
```

Frontend dependencies are maintained through the frontend package configuration.

## 8. Documentation

Documentation should be updated when a change introduces or modifies:

- architecture
- development conventions
- important technical decisions
- project structure
- externally relevant behavior

Documentation should remain concise and should avoid duplicating information that can be obtained directly from the source code.

## 9. Development Principle

Prefer simple, understandable solutions over unnecessary complexity.

New infrastructure, abstractions, or dependencies should be introduced when they solve an actual project requirement.

CentFlow is being developed incrementally, so the repository structure and conventions should evolve alongside the application rather than anticipating every future requirement.