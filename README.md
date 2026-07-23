# Kiln & Co. — A vulnerable coffee storefront

A small e-commerce demo built to showcase both sides of a security engagement:
breaking in as an attacker, and investigating as a defender — using the same
vulnerability, the same app, the same logs.

**The vulnerability class: IDOR / Broken Object Level Authorization (BOLA).**
This is currently #1 on the OWASP API Security Top 10. Every order in the
store has a numeric ID. The app checks that you're *logged in* before showing
you an order, but never checks that the order actually *belongs to you*. Any
logged-in customer can change the number in the URL and view or edit anyone
else's order — shipping address, phone number, masked card digits, all of it.

Built for security education and portfolio use. Run only on your own machine.

## Setup

```bash
cd kiln-idor-demo
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python3 app.py
```

Visit `http://localhost:5000`. Two demo accounts already exist:

| Username | Password   |
|----------|------------|
| sam      | coffee123  |
| alex     | coffee123  |

Each already has a couple of orders seeded, so the IDOR has real data to
expose from the very first run — you don't need to place a fresh order to
demo it.

## Live walkthrough

**1. Log in as `sam`.** Go to "My Orders." You'll see Sam's own orders,
correctly scoped — this list view checks ownership properly. That's
realistic and worth pointing out: the bug isn't everywhere, it's one click
away.

**2. Click into one of Sam's orders.** Note the URL: `/order/1`. Note the
order ticket shows Sam's real shipping address and phone number.

**3. Change the URL to `/order/2`.** That order belongs to Alex. The page
loads anyway, showing Alex's shipping address, phone number, and masked card
digits — Sam was never checked against the order's actual owner.

**4. Go further: use the "Update shipping address" form on Alex's order** and
save a new address. It saves — Sam just modified another customer's order.
There's also a "Cancel this order" button that's equally unprotected.

**5. Switch hats.** Log out, and imagine Alex just used the "Report a
problem" form on the Account page to say "I saw an order I didn't place."
That's the trigger for the investigation.

**6. Run the analyzer:**

```bash
python3 analyze_logs.py
```

It reads `requests.log` (written automatically while the app runs) and
cross-references every `/order/<id>` request against the real ownership data
in `kiln.db`. It will print exactly what Sam did: which order, when, from
what IP, and whether it was a view or a modification — plus a separate check
for whether the same user touched more than one order that wasn't theirs,
which is the difference between an accidental fluke and someone
systematically scanning IDs.

