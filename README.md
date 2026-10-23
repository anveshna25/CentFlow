# CentFlow

CentFlow is a market intelligence platform for tracking financial markets, analyzing assets, and exploring data-driven insights.

## Status

🚧 **In Development**

CentFlow is currently being built from the ground up as an open-source project.

## Tech Stack

### Frontend

- React
- Vite
- JavaScript / JSX

### Backend

- Python
- FastAPI

## Project Structure

```text
CentFlow/
├── backend/        # Backend services and server-side code
├── docs/           # Project architecture and technical documentation
├── frontend/       # React frontend application
├── .gitignore
├── LICENSE
└── README.md
```

## Development

The project is currently in its foundation stage.

The initial development focus is on establishing the project structure, frontend foundation, backend foundation, and development conventions.

### Development Setup

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs locally at:

`http://localhost:5173`

#### Backend

```bash
cd backend
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload
```

The backend runs locally at:

`http://127.0.0.1:8000`

FastAPI documentation is available at:

`http://127.0.0.1:8000/docs`

#### Environment

Create a local `.env` file from `.env.example`:

```text
copy .env.example .env
```

The `.env` file is local-only and must not be committed.

Application functionality will be introduced progressively in later phases.

## Documentation

Project architecture and technical documentation can be found in the [`docs/`](docs/) directory.

## License

See the [LICENSE](LICENSE) file for licensing information.