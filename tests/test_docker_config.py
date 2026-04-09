"""S82: Docker production configuration validation tests.

Validates Dockerfile, docker-compose, nginx config, and .dockerignore
without requiring Docker daemon — pure file/content assertions.
"""

import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestDockerfileProd:
    """Validate Dockerfile.prod structure and best practices."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / "Dockerfile.prod"
        self.content = self.path.read_text(encoding="utf-8")

    def test_exists(self):
        assert self.path.exists()

    def test_multi_stage_build(self):
        assert "FROM python:3.12-slim AS builder" in self.content
        assert "FROM python:3.12-slim AS runtime" in self.content

    def test_non_root_user(self):
        assert "useradd" in self.content
        assert "USER vezir" in self.content

    def test_no_cache_dir(self):
        assert "--no-cache-dir" in self.content

    def test_healthcheck_present(self):
        assert "HEALTHCHECK" in self.content
        assert "/api/v1/health" in self.content

    def test_port_8003_exposed(self):
        assert "EXPOSE 8003" in self.content

    def test_copies_from_builder(self):
        assert "COPY --from=builder" in self.content

    def test_removes_test_directories(self):
        assert "rm -rf /app/agent/tests" in self.content

    def test_environment_variables(self):
        assert "PYTHONDONTWRITEBYTECODE=1" in self.content
        assert "PYTHONUNBUFFERED=1" in self.content

    def test_uvicorn_workers(self):
        assert '"--workers"' in self.content


class TestFrontendDockerfile:
    """Validate frontend/Dockerfile structure."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / "frontend" / "Dockerfile"
        self.content = self.path.read_text(encoding="utf-8")

    def test_exists(self):
        assert self.path.exists()

    def test_multi_stage_build(self):
        assert "FROM node:20-alpine AS builder" in self.content
        assert "FROM nginx:1.27-alpine AS runtime" in self.content

    def test_npm_ci(self):
        assert "npm ci" in self.content

    def test_npm_run_build(self):
        assert "npm run build" in self.content

    def test_copies_dist(self):
        assert "COPY --from=builder /build/dist" in self.content

    def test_port_4000(self):
        assert "EXPOSE 4000" in self.content

    def test_healthcheck(self):
        assert "HEALTHCHECK" in self.content

    def test_nginx_config_copied(self):
        assert "nginx.conf" in self.content


class TestNginxConfig:
    """Validate nginx.conf for SPA + API proxy."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / "frontend" / "nginx.conf"
        self.content = self.path.read_text(encoding="utf-8")

    def test_exists(self):
        assert self.path.exists()

    def test_listens_on_4000(self):
        assert "listen 4000" in self.content

    def test_spa_fallback(self):
        assert "try_files" in self.content
        assert "/index.html" in self.content

    def test_api_proxy(self):
        assert "proxy_pass http://vezir-api:8003" in self.content

    def test_sse_support(self):
        assert "proxy_buffering off" in self.content
        assert "proxy_cache off" in self.content

    def test_gzip_enabled(self):
        assert "gzip on" in self.content

    def test_static_asset_caching(self):
        assert "expires 1y" in self.content
        assert "immutable" in self.content


class TestDockerComposeProd:
    """Validate docker-compose.prod.yml structure."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / "docker-compose.prod.yml"
        self.content = self.path.read_text(encoding="utf-8")

    def test_exists(self):
        assert self.path.exists()

    def test_api_uses_prod_dockerfile(self):
        assert "Dockerfile.prod" in self.content

    def test_frontend_service(self):
        assert "vezir-frontend" in self.content

    def test_frontend_port_4000(self):
        assert '"4000:4000"' in self.content

    def test_resource_limits(self):
        assert "memory: 512M" in self.content  # api
        assert "memory: 128M" in self.content  # frontend

    def test_security_hardening(self):
        assert "read_only: true" in self.content
        assert "no-new-privileges" in self.content

    def test_frontend_depends_on_api(self):
        assert "service_healthy" in self.content


class TestDockerComposeBase:
    """Validate base docker-compose.yml still valid."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / "docker-compose.yml"
        self.content = self.path.read_text(encoding="utf-8")

    def test_api_service(self):
        assert "vezir-api" in self.content
        assert '"8003:8003"' in self.content

    def test_jaeger_service(self):
        assert "jaeger" in self.content

    def test_grafana_service(self):
        assert "grafana" in self.content


class TestDockerignore:
    """Validate .dockerignore excludes unnecessary files."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / ".dockerignore"
        self.content = self.path.read_text(encoding="utf-8")

    def test_excludes_git(self):
        assert ".git" in self.content

    def test_excludes_docs(self):
        assert "docs/" in self.content

    def test_excludes_tests(self):
        assert "agent/tests/" in self.content
        assert "tests/" in self.content

    def test_excludes_node_modules(self):
        assert "node_modules" in self.content

    def test_excludes_evidence(self):
        assert "evidence/" in self.content

    def test_excludes_github(self):
        assert ".github/" in self.content


class TestCIWorkflow:
    """Validate docker-build.yml workflow."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = ROOT / ".github" / "workflows" / "docker-build.yml"
        self.content = self.path.read_text(encoding="utf-8")

    def test_exists(self):
        assert self.path.exists()

    def test_triggers_on_push_and_pr(self):
        assert "push:" in self.content
        assert "pull_request:" in self.content

    def test_builds_api_image(self):
        assert "Dockerfile.prod" in self.content
        assert "vezir-api:test" in self.content

    def test_builds_frontend_image(self):
        assert "vezir-frontend:test" in self.content

    def test_image_size_check(self):
        assert "Image size" in self.content

    def test_smoke_test(self):
        assert "Health check passed" in self.content

    def test_compose_validation(self):
        assert "compose" in self.content
        assert "config" in self.content

    def test_read_only_permissions(self):
        assert "contents: read" in self.content
