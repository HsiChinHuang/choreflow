# Design System

## Overview

The UI uses Bootstrap 5 for styling and layout.

## Framework

- **Bootstrap 5** via CDN in `base.html`.
- Templates use Bootstrap grid, cards, badges, and navbar components.

## Template Structure

- `base.html` — Base template with Bootstrap 5 CDN, navbar, and block definitions (`title`, `extra_css`, `content`, `extra_js`).
- `chore_card.html` — Reusable partial for displaying a single chore assignment.
- `notification_list.html` — Partial for rendering notifications.

## Static Files

- Static files are served from `static/` directories within apps.
