"""Tests for Math Service."""
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_add():
    r = client.post("/api/add", json={"a": 10, "b": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == 15
    assert data["operation"] == "add"


def test_subtract():
    r = client.post("/api/subtract", json={"a": 10, "b": 3})
    assert r.status_code == 200
    assert r.json()["result"] == 7


def test_multiply():
    r = client.post("/api/multiply", json={"a": 4, "b": 6})
    assert r.status_code == 200
    assert r.json()["result"] == 24


def test_divide():
    r = client.post("/api/divide", json={"a": 20, "b": 4})
    assert r.status_code == 200
    assert r.json()["result"] == 5.0


def test_divide_by_zero():
    r = client.post("/api/divide", json={"a": 10, "b": 0})
    assert r.status_code == 400
    assert "Sifira bolme" in r.json()["detail"]


def test_add_negative():
    r = client.post("/api/add", json={"a": -5, "b": -3})
    assert r.status_code == 200
    assert r.json()["result"] == -8


def test_multiply_decimal():
    r = client.post("/api/multiply", json={"a": 2.5, "b": 4})
    assert r.status_code == 200
    assert r.json()["result"] == 10.0


def test_factorial():
    r = client.post("/api/factorial", json={"n": 5})
    assert r.status_code == 200
    assert r.json()["result"] == 120
    assert r.json()["operation"] == "factorial"


def test_factorial_zero():
    r = client.post("/api/factorial", json={"n": 0})
    assert r.status_code == 200
    assert r.json()["result"] == 1


def test_factorial_negative():
    r = client.post("/api/factorial", json={"n": -3})
    assert r.status_code == 400
    assert "Negatif" in r.json()["detail"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
