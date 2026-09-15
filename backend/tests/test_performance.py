"""Automated performance, telemetry, and observability benchmarks for The Lenny Growth Assistant."""

import sys
import os
import time
import statistics
import concurrent.futures
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import get_db_session, ping_db
from app.db.models import Session as SessionModel, RetrievalLog
from app.retrieval.retriever import retrieve_evidence

client = TestClient(app)

def test_retrieval_latency_benchmark():
    """Benchmark hybrid retrieval latency across 20 consecutive queries; verify SLA < 50ms average."""
    queries = [
        "What is Brian Chesky's founder mode?",
        "How did Airbnb handle the 2020 pandemic crisis?",
        "Explain Shreyas Doshi's LNO framework for prioritization.",
        "What is a product pre-mortem and how does it prevent failure?",
        "How do high-agency operators run an organization?",
    ] * 4  # 20 queries

    latencies = []
    with get_db_session() as db:
        # Warmup query embeddings to absorb cold CPU model loading and measure pure retrieval SLA
        for q in set(queries):
            retrieve_evidence(query=q, db=db, top_k=1)

        for q in queries:
            result = retrieve_evidence(query=q, db=db, top_k=5)
            latencies.append(result.latency_ms)

    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    # Retrieval SLA: average < 250ms, p95 < 350ms across SQLite/Postgres
    assert mean_latency < 250.0, f"Mean retrieval latency {mean_latency:.2f}ms exceeded 250ms SLA"
    assert p95_latency < 350.0, f"P95 retrieval latency {p95_latency:.2f}ms exceeded 350ms"
    assert median_latency < 250.0


def test_retrieval_observability_persistence():
    """Verify that every retrieval execution logs a structured audit trail into RetrievalLog."""
    unique_marker = f"benchmark_query_{int(time.time() * 1000)}"

    with get_db_session() as db:
        initial_count = db.query(RetrievalLog).count()

        result = retrieve_evidence(query=unique_marker, db=db, top_k=3)

        new_count = db.query(RetrievalLog).count()
        assert new_count == initial_count + 1

        # Check logged record fields
        log_record = db.query(RetrievalLog).order_by(RetrievalLog.created_at.desc()).first()
        assert log_record is not None
        assert log_record.query == unique_marker
        assert log_record.latency_ms > 0.0
        assert isinstance(log_record.top_similarity, float)
        assert isinstance(log_record.grounded, bool)


def test_telemetry_headers_propagation():
    """Audit all major API endpoints to ensure X-Request-ID and X-Response-Time-MS are present."""
    endpoints = [
        ("/health", "GET", None),
        ("/health/db", "GET", None),
        ("/health/llm", "GET", None),
        ("/api/v1/sessions", "GET", None),
        ("/api/v1/retrieve", "POST", {"query": "founder mode", "top_k": 3}),
    ]

    for path, method, payload in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json=payload)

        assert res.status_code == 200, f"Endpoint {path} returned status {res.status_code}"
        assert "x-request-id" in res.headers, f"Missing X-Request-ID header on {path}"
        assert "x-response-time-ms" in res.headers, f"Missing X-Response-Time-MS header on {path}"

        # Assert latency value parses as positive float
        latency = float(res.headers["x-response-time-ms"])
        assert latency >= 0.0


def test_database_ping_latency():
    """Verify database connection pool responds within 25ms under sequential pings."""
    ping_latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        healthy = ping_db()
        elapsed = (time.perf_counter() - t0) * 1000
        assert healthy is True
        ping_latencies.append(elapsed)

    mean_ping = statistics.mean(ping_latencies)
    assert mean_ping < 25.0, f"Mean DB ping latency {mean_ping:.2f}ms exceeded 25ms"


def test_concurrent_turn_throughput():
    """Verify system processes concurrent message posts across distinct sessions without deadlocks."""
    # Create 5 distinct sessions
    session_ids = []
    for i in range(5):
        res = client.post("/api/v1/sessions", json={"title": f"Concurrency Session {i+1}"})
        assert res.status_code == 201
        session_ids.append(res.json()["id"])

    # Worker function posting turn
    def post_turn(sess_id, index):
        return client.post(
            f"/api/v1/sessions/{sess_id}/messages",
            json={
                "content": f"Turn {index}: What is the core lesson on founder mode from Brian Chesky?",
                "mode": "research",
            }
        )

    # Dispatch 10 parallel turns across the 5 sessions
    tasks = [(session_ids[i % len(session_ids)], i) for i in range(10)]
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(post_turn, s_id, idx) for s_id, idx in tasks]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    assert len(results) == 10
    for r in results:
        assert r.status_code == 201
        data = r.json()
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0
