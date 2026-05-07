"""
Tests for the /api/restocking endpoint that submits internal restocking orders.
"""
from datetime import datetime

import pytest


# Lead times mirrored from server/main.py LEAD_TIMES — keep in sync.
EXPECTED_LEAD_DAYS = {"San Francisco": 7, "London": 10, "Tokyo": 14}
DEFAULT_LEAD_DAYS = 10


def _payload(items, budget=None):
    body = {"items": items}
    if budget is not None:
        body["budget"] = budget
    return body


def _days_between(order_date_iso: str, expected_iso: str) -> int:
    order_date = datetime.fromisoformat(order_date_iso)
    expected = datetime.fromisoformat(expected_iso)
    return (expected - order_date).days


class TestRestockingEndpoint:
    """Test suite for POST /api/restocking."""

    def test_submit_single_item_returns_one_submitted_order(self, client):
        """A single-item restocking submission returns one Submitted order."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {
                    "sku": "PCB-001",
                    "name": "Single Layer PCB Assembly",
                    "quantity": 50,
                    "unit_cost": 24.99,
                    "warehouse": "San Francisco",
                    "category": "Circuit Boards",
                }
            ], budget=5000),
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        created = data[0]
        assert created["status"] == "Submitted"
        assert created["customer"] == "Internal Restocking"
        assert created["warehouse"] == "San Francisco"
        assert created["category"] == "Circuit Boards"
        assert created["actual_delivery"] is None
        assert created["order_number"].startswith("ORD-")
        assert isinstance(created["items"], list)
        assert len(created["items"]) == 1
        assert created["items"][0]["sku"] == "PCB-001"
        assert created["items"][0]["quantity"] == 50
        # Existing orders.json uses unit_price on line items.
        assert created["items"][0]["unit_price"] == 24.99

    def test_grouping_creates_one_order_per_warehouse(self, client):
        """Submitting items across multiple warehouses creates one order per warehouse."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "AAA-1", "name": "A", "quantity": 1, "unit_cost": 10.0,
                 "warehouse": "San Francisco", "category": "Circuit Boards"},
                {"sku": "AAA-2", "name": "A2", "quantity": 2, "unit_cost": 10.0,
                 "warehouse": "San Francisco", "category": "Circuit Boards"},
                {"sku": "BBB-1", "name": "B", "quantity": 3, "unit_cost": 20.0,
                 "warehouse": "London", "category": "Sensors"},
                {"sku": "CCC-1", "name": "C", "quantity": 4, "unit_cost": 5.0,
                 "warehouse": "Tokyo", "category": "Sensors"},
            ]),
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3

        warehouses = {o["warehouse"] for o in data}
        assert warehouses == {"San Francisco", "London", "Tokyo"}

        sf_order = next(o for o in data if o["warehouse"] == "San Francisco")
        assert len(sf_order["items"]) == 2

    def test_lead_time_per_warehouse(self, client):
        """expected_delivery − order_date matches the configured per-warehouse lead time."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "X-SF", "name": "X", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "San Francisco", "category": "Circuit Boards"},
                {"sku": "X-LD", "name": "X", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "London", "category": "Sensors"},
                {"sku": "X-TY", "name": "X", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "Tokyo", "category": "Sensors"},
            ]),
        )
        assert response.status_code == 200

        for order in response.json():
            expected = EXPECTED_LEAD_DAYS[order["warehouse"]]
            actual = _days_between(order["order_date"], order["expected_delivery"])
            assert actual == expected, (
                f"{order['warehouse']} should have a {expected}-day lead time, got {actual}"
            )

    def test_unknown_warehouse_falls_back_to_default(self, client):
        """A warehouse without a lead-time mapping uses the 10-day default."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "X-001", "name": "X", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "Atlantis", "category": "Sensors"},
            ]),
        )
        assert response.status_code == 200

        order = response.json()[0]
        assert order["warehouse"] == "Atlantis"
        actual = _days_between(order["order_date"], order["expected_delivery"])
        assert actual == DEFAULT_LEAD_DAYS

    def test_total_value_matches_line_items(self, client):
        """total_value equals sum(qty * unit_cost) for the warehouse's items."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "T-1", "name": "T1", "quantity": 5, "unit_cost": 10.0,
                 "warehouse": "London", "category": "Sensors"},
                {"sku": "T-2", "name": "T2", "quantity": 3, "unit_cost": 7.5,
                 "warehouse": "London", "category": "Sensors"},
            ]),
        )
        assert response.status_code == 200

        order = response.json()[0]
        expected_total = (5 * 10.0) + (3 * 7.5)
        assert abs(order["total_value"] - expected_total) < 0.01

    def test_submitted_order_appears_in_get_orders(self, client):
        """A submitted order is visible from a subsequent GET /api/orders."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "VIS-1", "name": "Visible", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "San Francisco", "category": "Circuit Boards"},
            ]),
        )
        assert response.status_code == 200
        created_id = response.json()[0]["id"]

        listing = client.get("/api/orders").json()
        match = next((o for o in listing if o["id"] == created_id), None)
        assert match is not None
        assert match["status"] == "Submitted"

    def test_empty_items_returns_400(self, client):
        """Empty items list is rejected with a 400."""
        response = client.post("/api/restocking", json=_payload([]))
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_filter_by_submitted_status(self, client):
        """Submitted orders are reachable via the existing status filter on /api/orders."""
        client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "FILT-1", "name": "Filt", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "Tokyo", "category": "Sensors"},
            ]),
        )

        response = client.get("/api/orders?status=Submitted")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for order in data:
            assert order["status"].lower() == "submitted"

    def test_category_inferred_from_items(self, client):
        """The order's category is the most common category across its line items."""
        response = client.post(
            "/api/restocking",
            json=_payload([
                {"sku": "CAT-1", "name": "A", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "London", "category": "Sensors"},
                {"sku": "CAT-2", "name": "B", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "London", "category": "Sensors"},
                {"sku": "CAT-3", "name": "C", "quantity": 1, "unit_cost": 1.0,
                 "warehouse": "London", "category": "Circuit Boards"},
            ]),
        )
        assert response.status_code == 200

        order = response.json()[0]
        assert order["category"] == "Sensors"
