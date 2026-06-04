# Frontend Architecture

## Overview

The SceneIQ frontend is a React-based single-page application providing production management, tax incentive analysis, scheduling, compliance tracking, and AI-assisted workflows.

The application is built using React, TypeScript, Vite, and Tailwind CSS.

---

## Technology Stack

| Layer | Technology |
|---------|---------|
| Framework | React 19 |
| Language | TypeScript 5 |
| Build Tool | Vite 7 |
| Styling | Tailwind CSS 4 |
| HTTP Client | Axios |
| Linting | ESLint 9 |
| Package Manager | npm |
| Deployment Target | Railway |

---

## Frontend Directory Structure

```text
frontend/
├── src/
├── public/
├── dist/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── index.html
```

---

## Core Responsibilities

### Dashboard

Provides operational visibility into:

- Active productions
- Incentive estimates
- Spend analysis
- Production metrics

### Production Management

Allows users to:

- Create productions
- Manage jurisdictions
- Monitor qualification status
- Track compliance activities

### Incentive Analysis

Provides:

- Incentive calculators
- Jurisdiction comparisons
- Scenario analysis
- Credit estimation

### Scheduling

Provides interfaces for:

- Script breakdown imports
- Stripboard management
- Day Out of Days reporting
- Call sheet generation

### Administration

Provides:

- User management
- System administration
- Rule review workflows

---

## Frontend Design Principles

### Component Reusability

UI elements should be implemented as reusable components whenever possible.

### API-Driven Design

Business logic should reside in backend services.

Frontend should focus on:

- Presentation
- User interaction
- State management
- API communication

### Responsive Design

Support:

- Desktop
- Tablet
- Mobile

using Tailwind responsive breakpoints.

---

## Current Assessment

### Strengths

- Modern React stack
- TypeScript adoption
- Vite build performance
- Tailwind design system
- ESLint enforcement

### Improvement Opportunities

- Add frontend architecture diagrams
- Increase component documentation
- Add Storybook for UI components
- Expand frontend testing coverage
- Introduce error boundary strategy
- Add performance monitoring

---

## Future Enhancements

- Design system documentation
- Accessibility compliance audits
- Component library standardization
- Analytics instrumentation
- Enterprise role-aware UI controls