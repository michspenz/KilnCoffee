from conftest import login


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_login_with_valid_credentials_succeeds(client):
    resp = login(client, "sam")
    assert b"Welcome back" in resp.data


def test_login_with_invalid_credentials_fails(client):
    resp = client.post("/login", data={"username": "sam", "password": "wrong"}, follow_redirects=True)
    assert b"Invalid username or password" in resp.data


def test_register_new_account_then_login(client):
    resp = client.post(
        "/register",
        data={"full_name": "New Person", "email": "new@example.com", "username": "newperson", "password": "hunter2"},
        follow_redirects=True,
    )
    assert b"Account created" in resp.data

    resp = login(client, "newperson", password="hunter2")
    assert b"Welcome back" in resp.data


def test_register_duplicate_username_is_rejected(client):
    client.post(
        "/register",
        data={"full_name": "A", "email": "a@example.com", "username": "sam", "password": "x"},
        follow_redirects=True,
    )
    resp = client.post(
        "/register",
        data={"full_name": "B", "email": "b@example.com", "username": "sam", "password": "y"},
        follow_redirects=True,
    )
    assert b"already taken" in resp.data


# ---------------------------------------------------------------------------
# Storefront
# ---------------------------------------------------------------------------

def test_storefront_lists_seeded_products(client):
    resp = client.get("/")
    assert b"Ember Reserve" in resp.data
    assert b"Meadow Light" in resp.data


def test_product_detail_page_loads(client):
    resp = client.get("/product/1")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Access control on core pages
# ---------------------------------------------------------------------------

def test_my_orders_requires_login(client):
    resp = client.get("/orders", follow_redirects=True)
    assert b"Please log in first" in resp.data


def test_my_orders_only_shows_own_orders(client):
    login(client, "sam")
    resp = client.get("/orders")
    # Sam owns orders #1 and #3 in the seed data, not #2 or #4
    assert b"#0001" in resp.data
    assert b"#0003" in resp.data
    assert b"#0002" not in resp.data
    assert b"#0004" not in resp.data


# ---------------------------------------------------------------------------
# The vulnerability itself, and the fix
# ---------------------------------------------------------------------------

def test_vulnerable_mode_allows_viewing_someone_elses_order(client):
    """This test documents the bug on purpose. It should PASS while the app
    is vulnerable, and is expected to start FAILING once SECURE_MODE is on —
    see the paired secure-mode test below."""
    login(client, "sam")
    resp = client.get("/order/2")  # order #2 belongs to alex, not sam
    assert resp.status_code == 200
    assert b"Rivera" in resp.data  # Alex's name, visible to Sam


def test_vulnerable_mode_allows_editing_someone_elses_order(client):
    login(client, "sam")
    resp = client.post("/order/2/update", data={"shipping_address": "Tampered Address"}, follow_redirects=True)
    assert b"Tampered Address" in resp.data


def test_secure_mode_blocks_viewing_someone_elses_order(client):
    client.application.config["SECURE_MODE"] = True
    login(client, "sam")
    resp = client.get("/order/2", follow_redirects=True)
    assert b"have permission to view" in resp.data
    assert b"Rivera" not in resp.data


def test_secure_mode_blocks_editing_someone_elses_order(client):
    client.application.config["SECURE_MODE"] = True
    login(client, "sam")
    resp = client.post("/order/2/update", data={"shipping_address": "Tampered Address"}, follow_redirects=True)
    assert b"have permission to view" in resp.data
    assert b"Tampered Address" not in resp.data


def test_secure_mode_still_allows_viewing_own_order(client):
    client.application.config["SECURE_MODE"] = True
    login(client, "sam")
    resp = client.get("/order/1")  # order #1 genuinely belongs to sam
    assert resp.status_code == 200
    assert b"Whitfield" in resp.data


# ---------------------------------------------------------------------------
# Report flow
# ---------------------------------------------------------------------------

def test_report_a_problem_requires_login(client):
    resp = client.post("/account/report", data={"message": "help"}, follow_redirects=True)
    assert b"Please log in first" in resp.data


def test_report_a_problem_succeeds_when_logged_in(client):
    login(client, "alex")
    resp = client.post("/account/report", data={"message": "I saw an order I didn't place"}, follow_redirects=True)
    assert b"security team has been notified" in resp.data
