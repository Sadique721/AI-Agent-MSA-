import pytest
from coding.CodingMemory import CodingMemory

@pytest.fixture
def memory():
    return CodingMemory()

def test_memory_init(memory):
    assert memory is not None
    assert memory.rag is not None

def test_store_coding_project(memory):
    res = memory.store("Create project", {"explanation": "React scaffolding"}, "coding_project")
    assert res is True

def test_store_coding_fix(memory):
    res = memory.store("Fix bug", {"suggestion": "Add null check"}, "coding_fix")
    assert res is True

def test_store_coding_review(memory):
    res = memory.store("Review code", {"explanation": "Quality is B"}, "coding_review")
    assert res is True

def test_store_coding_reference(memory):
    res = memory.store("Reference", {"explanation": "Docs link"}, "coding_reference")
    assert res is True

def test_store_coding_template(memory):
    res = memory.store("Template", {"explanation": "Flask boilerplate"}, "coding_template")
    assert res is True

def test_store_empty_payload(memory):
    res = memory.store("Empty", {}, "coding_project")
    assert res is True

def test_store_none_values(memory):
    res = memory.store("", {}, "coding_project")
    assert res is False

def test_search_results(memory):
    memory.store("React app", {"explanation": "React dashboard app"}, "coding_project")
    results = memory.search("React app")
    assert isinstance(results, list)

@pytest.mark.parametrize("idx", range(12))
def test_memory_param_store(memory, idx):
    res = memory.store(f"Prompt {idx}", {"explanation": f"Response {idx}"}, "coding_reference")
    assert res is True
