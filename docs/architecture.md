# CentFlow Architecture

## 1. Project Overview

CentFlow is a market intelligence platform for tracking financial markets, analyzing assets, and exploring data-driven insights.

The project is being developed as an open-source application with a separated frontend and backend architecture.

## 2. Technology Stack

### Frontend

- React
- Vite
- JavaScript / JSX

### Backend

- Python
- FastAPI

## 3. Repository Structure

```text
CentFlow/
├── backend/        # Backend services and server-side code
├── docs/           # Project architecture and technical documentation
├── frontend/       # React frontend application
├── .gitignore
├── LICENSE
└── README.md

## 4. Directory Responsibilities

### `frontend/`

Contains the React-based client application, frontend components, assets, and frontend-specific configuration.

### `backend/`

Contains server-side services, APIs, business logic, domain models, database persistence, and backend-specific configuration. For architectural details, see [Backend Architecture](architecture/backend.md) and [Database Architecture](architecture/database.md).

### `docs/`

Contains project architecture, technical decisions, development conventions, and other project documentation.

## 5. Current Phase

This structure represents the initial project foundation.

Application-specific architecture, backend services, database systems, external integrations, and deployment infrastructure will be introduced progressively as the project develops.

## 6. Architecture Principles

- Keep frontend and backend responsibilities clearly separated.
- Keep project documentation centralized under `docs/`.
- Keep the initial structure simple and easy to extend.
- Introduce additional infrastructure when it is required by the application.
- Avoid implementing application-specific systems before their requirements are defined.
- Keep the repository organized so future development can build upon the initial foundation.