# CentFlow Domain Model

## Purpose

This document defines the core domain terminology used across CentFlow.

The domain model establishes the conceptual foundation for the backend, database, API, frontend, and future market-intelligence features.

## Core Entities

### Asset

An Asset represents a financial or market-related underlying entity that can be tracked within CentFlow.

Examples include equities, currencies, commodities, indices, or other supported asset classes.

An Asset describes the underlying economic/security concept rather than a particular trading venue.

### Instrument

An Instrument represents a specific identifiable financial security or tradable representation of an asset.

An Instrument has a symbol and may be associated with an Exchange and Market.

Examples:

- AAPL
- MSFT
- RELIANCE

### Exchange

An Exchange represents a marketplace or trading venue where instruments are listed or traded.

Examples:

- NASDAQ
- NYSE
- NSE
- BSE

### Market

A Market represents a logical market or market segment in which instruments are tracked.

A Market may describe a geographic, regional, asset-class, or other logical grouping.

### Price

A Price represents an observed price value for an Instrument at a particular point in time.

A price observation contains:

- Instrument
- Value
- Currency
- Timestamp

Price observations form the basis for historical and real-time market-data functionality.

### Watchlist

A Watchlist is a user-defined collection of Instruments that the user wants to monitor.

A Watchlist has a name and contains zero or more Instruments.

### Portfolio

A Portfolio represents a collection of financial Positions managed together.

A Portfolio has a name and contains zero or more Positions.

### Position

A Position represents a holding of an Instrument within a Portfolio.

A Position contains:

- Instrument
- Quantity
- Average price
- Currency

## Relationships

```text
Asset
  │
  └── Instrument
        ├── Exchange
        ├── Market
        └── Price

Watchlist
  └── Instrument

Portfolio
  └── Position
        └── Instrument