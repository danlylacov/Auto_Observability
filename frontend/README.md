# Auto Observability Frontend

Frontend application for Auto Observability built with Vue 3, TypeScript, and Vite.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Update `.env` with your API URL:
```
VITE_API_URL=http://localhost:8081
```

## Development

Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build

Build for production:
```bash
npm run build
```

## Features

- View all containers
- Start/Stop/Remove containers
- View container details
- Generate Prometheus configuration
- Start Prometheus exporters

