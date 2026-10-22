# CentFlow Architecture

## Overview

CentFlow is being developed as a market intelligence platform for tracking financial markets, analyzing assets, and providing data-driven insights.

## Initial Architecture

```text
┌─────────────────────┐
│      Frontend       │
│    React + Vite     │
└──────────┬──────────┘
           │
           │ HTTP / API
           ▼
┌─────────────────────┐
│       Backend       │
│  Python + FastAPI   │
└──────────┬──────────┘
           │
           ▼
     Future Services
     - Market Data
     - Database
     - Analytics
     - Intelligence