"""
tests/test_project_generator.py
================================
Unit tests for coding/ProjectGenerator.py — Phase-3 Coding Agent.
Covers all 5 project types, blueprint structure, file content, and edge cases.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coding.ProjectGenerator import ProjectGenerator


@pytest.fixture
def gen():
    """ProjectGenerator without LLM."""
    return ProjectGenerator(llm=None)


# ── Spring Boot Project ──────────────────────────────────────────────────────

class TestSpringBootProject:
    """Spring Boot project scaffolding."""

    def test_springboot_project_type(self, gen):
        result = gen.generate("springboot", "my-api")
        assert result["project_type"] == "springboot"

    def test_springboot_name(self, gen):
        result = gen.generate("springboot", "my-api")
        assert result["name"] == "my-api"

    def test_springboot_has_directories(self, gen):
        result = gen.generate("springboot", "demo")
        assert "directories" in result["blueprint"]
        assert len(result["blueprint"]["directories"]) > 0

    def test_springboot_has_pom_xml(self, gen):
        result = gen.generate("springboot", "demo")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "pom.xml" in paths

    def test_springboot_has_application_yml(self, gen):
        result = gen.generate("springboot", "demo")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert any("application.yml" in p for p in paths)

    def test_springboot_has_main_class(self, gen):
        result = gen.generate("springboot", "demo")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert any("Application.java" in p for p in paths)

    def test_springboot_has_dockerfile(self, gen):
        result = gen.generate("springboot", "demo")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "Dockerfile" in paths

    def test_springboot_has_readme(self, gen):
        result = gen.generate("springboot", "demo")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "README.md" in paths

    def test_springboot_pom_contains_dependencies(self, gen):
        result = gen.generate("springboot", "demo")
        pom = [f for f in result["blueprint"]["files"] if f["path"] == "pom.xml"][0]
        assert "spring-boot-starter-web" in pom["content"]
        assert "spring-boot-starter-data-jpa" in pom["content"]

    def test_springboot_main_has_annotation(self, gen):
        result = gen.generate("springboot", "demo")
        main = [f for f in result["blueprint"]["files"] if "Application.java" in f["path"]][0]
        assert "@SpringBootApplication" in main["content"]

    def test_spring_keyword_triggers_springboot(self, gen):
        result = gen.generate("spring", "my-app")
        assert result["project_type"] == "springboot"


# ── Angular Project ──────────────────────────────────────────────────────────

class TestAngularProject:
    """Angular project scaffolding."""

    def test_angular_project_type(self, gen):
        result = gen.generate("angular", "my-app")
        assert result["project_type"] == "angular"

    def test_angular_has_package_json(self, gen):
        result = gen.generate("angular", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "package.json" in paths

    def test_angular_has_angular_json(self, gen):
        result = gen.generate("angular", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "angular.json" in paths

    def test_angular_has_app_component(self, gen):
        result = gen.generate("angular", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert any("app.component.ts" in p for p in paths)

    def test_angular_has_readme(self, gen):
        result = gen.generate("angular", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "README.md" in paths

    def test_angular_package_has_dependencies(self, gen):
        result = gen.generate("angular", "my-app")
        pkg = [f for f in result["blueprint"]["files"] if f["path"] == "package.json"][0]
        assert "@angular/core" in pkg["content"]


# ── React Project ────────────────────────────────────────────────────────────

class TestReactProject:
    """React project scaffolding."""

    def test_react_project_type(self, gen):
        result = gen.generate("react", "my-app")
        assert result["project_type"] == "react"

    def test_react_has_package_json(self, gen):
        result = gen.generate("react", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "package.json" in paths

    def test_react_has_app_js(self, gen):
        result = gen.generate("react", "my-app")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert any("App.js" in p for p in paths)

    def test_react_app_uses_react(self, gen):
        result = gen.generate("react", "my-app")
        app = [f for f in result["blueprint"]["files"] if "App.js" in f["path"]][0]
        assert "import React" in app["content"]


# ── Node.js Project ──────────────────────────────────────────────────────────

class TestNodeProject:
    """Node.js Express project scaffolding."""

    def test_nodejs_project_type(self, gen):
        result = gen.generate("nodejs", "my-server")
        assert result["project_type"] == "nodejs"

    def test_nodejs_has_server_js(self, gen):
        result = gen.generate("nodejs", "my-server")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "server.js" in paths

    def test_nodejs_has_dockerfile(self, gen):
        result = gen.generate("nodejs", "my-server")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "Dockerfile" in paths

    def test_nodejs_server_uses_express(self, gen):
        result = gen.generate("nodejs", "my-server")
        server = [f for f in result["blueprint"]["files"] if f["path"] == "server.js"][0]
        assert "express" in server["content"]

    def test_node_keyword_triggers_nodejs(self, gen):
        result = gen.generate("node", "my-server")
        assert result["project_type"] == "nodejs"


# ── Microservices / Docker Project ────────────────────────────────────────────

class TestMicroservicesProject:
    """Microservices Docker Compose project."""

    def test_microservices_project_type(self, gen):
        result = gen.generate("microservices", "my-cluster")
        assert result["project_type"] == "microservices"

    def test_microservices_has_compose(self, gen):
        result = gen.generate("microservices", "my-cluster")
        paths = [f["path"] for f in result["blueprint"]["files"]]
        assert "docker-compose.yml" in paths

    def test_microservices_compose_has_services(self, gen):
        result = gen.generate("microservices", "my-cluster")
        compose = [f for f in result["blueprint"]["files"] if f["path"] == "docker-compose.yml"][0]
        assert "services:" in compose["content"]
        assert "gateway" in compose["content"]

    def test_docker_keyword_triggers_microservices(self, gen):
        result = gen.generate("docker", "my-cluster")
        assert result["project_type"] == "microservices"


# ── Default Description ──────────────────────────────────────────────────────

class TestDefaultDescription:
    """Default description is generated if none provided."""

    def test_default_description_springboot(self, gen):
        result = gen.generate("springboot", "demo", "")
        readme = [f for f in result["blueprint"]["files"] if f["path"] == "README.md"][0]
        assert "demo" in readme["content"]

    def test_custom_description_in_readme(self, gen):
        result = gen.generate("nodejs", "my-api", "Custom REST API server")
        readme = [f for f in result["blueprint"]["files"] if f["path"] == "README.md"][0]
        assert "Custom REST API server" in readme["content"]


# ── Fallback ──────────────────────────────────────────────────────────────────

class TestFallback:
    """Unknown project types default to Node.js."""

    def test_unknown_type_defaults_to_nodejs(self, gen):
        result = gen.generate("unknown_framework", "test-app")
        assert result["project_type"] == "nodejs"


# ── Output Structure ─────────────────────────────────────────────────────────

class TestOutputStructure:
    """Verify all outputs conform to expected schema."""

    def test_result_has_project_type(self, gen):
        result = gen.generate("react", "app")
        assert "project_type" in result

    def test_result_has_name(self, gen):
        result = gen.generate("react", "app")
        assert "name" in result

    def test_result_has_blueprint(self, gen):
        result = gen.generate("react", "app")
        assert "blueprint" in result

    def test_blueprint_has_directories(self, gen):
        result = gen.generate("react", "app")
        assert "directories" in result["blueprint"]
        assert isinstance(result["blueprint"]["directories"], list)

    def test_blueprint_has_files(self, gen):
        result = gen.generate("react", "app")
        assert "files" in result["blueprint"]
        assert isinstance(result["blueprint"]["files"], list)

    def test_each_file_has_path_and_content(self, gen):
        result = gen.generate("springboot", "demo")
        for f in result["blueprint"]["files"]:
            assert "path" in f
            assert "content" in f
            assert len(f["content"]) > 0
