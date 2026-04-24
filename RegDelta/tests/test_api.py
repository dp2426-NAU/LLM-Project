from unittest.mock import MagicMock, patch

import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestIngestEndpoints:
    def test_ingest_regulation_missing_source(self, test_client):
        resp = test_client.post(
            "/api/v1/ingest/regulation",
            json={
                "regulation_id": "SEC-17a-4",
                "regulatory_body": "SEC",
                "title": "Electronic Records Rule",
                "version_tag": "2024-Q1",
            },
        )
        assert resp.status_code == 422

    def test_ingest_regulation_invalid_body(self, test_client):
        resp = test_client.post(
            "/api/v1/ingest/regulation",
            json={
                "regulation_id": "TEST-001",
                "regulatory_body": "INVALID_BODY",
                "title": "Test",
                "version_tag": "v1",
                "file_path": "/tmp/test.txt",
            },
        )
        assert resp.status_code == 422

    def test_ingest_policy_missing_source(self, test_client):
        resp = test_client.post(
            "/api/v1/ingest/policy",
            json={
                "policy_id": "POL-001",
                "title": "Test Policy",
                "department": "Compliance",
            },
        )
        assert resp.status_code == 422


class TestQueryEndpoint:
    def test_query_policies(self, test_client):
        with patch("api.routes.query.Retriever") as MockRetriever:
            MockRetriever.return_value.retrieve_policies.return_value = [
                {
                    "text": "Electronic records must be kept 7 years.",
                    "score": 0.88,
                    "metadata": {"policy_id": "POL-REC-001", "title": "Records Policy"},
                }
            ]
            resp = test_client.post(
                "/api/v1/query",
                json={"query": "record retention requirements", "corpus": "policies"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "hits" in data
        assert data["total"] >= 0

    def test_query_invalid_corpus(self, test_client):
        resp = test_client.post(
            "/api/v1/query",
            json={"query": "some query", "corpus": "invalid_corpus"},
        )
        assert resp.status_code == 422

    def test_get_nonexistent_report(self, test_client):
        resp = test_client.get("/api/v1/reports/nonexistent-report-id")
        assert resp.status_code == 404

    def test_list_reports_empty(self, test_client):
        resp = test_client.get("/api/v1/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
