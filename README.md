# KilnCoffee

A small Flask storefront demo built to illustrate IDOR / Broken Object Level Authorization (BOLA) in a realistic web app.

This project is intentionally vulnerable and is meant for security education, red-team practice, and defensive walkthroughs.

## What this demo shows

Every order in the storefront has a numeric ID. The app checks whether the user is logged in, but it does not verify that the order actually belongs to that user. A logged-in customer can change the order ID in the URL and view or modify another customer’s order details.

## Run locally

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

## Demo accounts

Two demo accounts are seeded for local use:

| Username | Password |
|----------|----------|
| sam      | coffee123 |
| alex     | coffee123 |

## Notes

- This project is intentionally insecure by design.
- It is meant for educational and portfolio use only.
- It is not a real business, payment system, or production application.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
