# KilnCoffee

A vulnerable Flask storefront demo for learning IDOR / broken object-level authorization (BOLA).

## What it demonstrates

This app intentionally exposes a broken order ownership check. A logged-in user can change the order ID in the URL and view or modify another user’s order.

## Run locally

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
python app.py
