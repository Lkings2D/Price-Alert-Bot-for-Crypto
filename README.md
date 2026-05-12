# Crypto Price Alert Tracker

## Overview

A real-time cryptocurrency price alert system built with FastAPI and deployed on Replit. The application monitors live market prices and sends Discord webhook notifications when configured price thresholds are reached.

The project includes a password-protected dashboard for managing alerts and supports multiple cryptocurrencies through exchange market data APIs.

## Features

* Real-time cryptocurrency price monitoring
* Discord webhook notifications
* Password-protected dashboard
* Add and remove alerts dynamically
* Support for multiple cryptocurrencies
* Lightweight in-memory alert management
* FastAPI backend with HTML dashboard
* Replit deployment support
* Automatic alert removal after trigger

## Supported Assets

* Bitcoin (BTC)
* Ethereum (ETH)
* Chainlink (LINK)
* Solana (SOL)
* XRP (XRP)
* Monero (XMR)

## Tech Stack

* Python
* FastAPI
* Jinja2 Templates
* AsyncIO
* WebSockets
* Requests / HTTP APIs
* Discord Webhooks
* Replit Hosting

## System Architecture

### Frontend

* HTML dashboard rendered with Jinja2 templates
* Password-protected access
* Alert management interface

### Backend

* FastAPI web server
* Async background price monitoring loop
* Cryptocurrency exchange API integration
* Discord notification system

### Hosting

* Replit deployment environment
* External uptime monitoring support

## Core Functionality

### Real-Time Monitoring

The application continuously monitors cryptocurrency market prices using exchange APIs and evaluates active alert conditions.

### Alert Management

Users can:

* Create price alerts
* Remove alerts manually
* Monitor active alerts from the dashboard

### Notification System

When a target price is reached:

1. The system sends a Discord webhook notification
2. The alert is automatically removed from memory
3. Monitoring continues for remaining alerts

## Security

* Password-protected dashboard access
* Environment variable management for secrets
* Hidden webhook credentials

## Environment Variables

```env
DISCORD_WEBHOOK=your_discord_webhook
DASH_PASSWORD=your_dashboard_password
```

## Deployment

Designed for deployment on Replit using Uvicorn.

### Run Command

```bash
uvicorn main:app --host 0.0.0.0 --port 3000
```

## Project Summary

Built a real-time cryptocurrency alert tracking platform using FastAPI, asynchronous Python workflows, and Discord webhooks. Implemented a password-protected dashboard for dynamic alert management and integrated live market monitoring through exchange APIs. Designed the application for lightweight deployment with persistent uptime support.
