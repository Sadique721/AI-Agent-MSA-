import pytest
from coding.CodingValidator import CodingValidator

@pytest.fixture
def validator():
    return CodingValidator()

def test_validator_init(validator):
    assert validator is not None

def test_validate_no_files(validator):
    res = validator.validate({})
    assert res["score"] == 0.0
    assert res["grade"] == "F"
    assert "No files generated." in res["errors"]

def test_validate_empty_path(validator):
    res = validator.validate({"files": [{"path": "", "content": "print('hello')"}]})
    assert res["score"] < 1.0
    assert "File path is empty." in res["errors"]

def test_validate_empty_content(validator):
    res = validator.validate({"files": [{"path": "hello.py", "content": ""}]})
    assert res["score"] < 1.0
    assert "File hello.py is empty." in res["errors"]

def test_validate_python_syntax_ok(validator):
    res = validator.validate({"files": [{"path": "hello.py", "content": "def run():\n    return 42"}]})
    assert res["score"] == 1.0
    assert len(res["errors"]) == 0

def test_validate_python_syntax_err(validator):
    res = validator.validate({"files": [{"path": "hello.py", "content": "def run(:"}]})
    assert res["score"] < 1.0
    assert any("syntax error" in err.lower() for err in res["errors"])

def test_validate_java_braces_err(validator):
    res = validator.validate({"files": [{"path": "Hello.java", "content": "public class Hello {"}]})
    assert res["score"] < 1.0
    assert any("braces" in err for err in res["errors"])

def test_validate_java_class_name_mismatch(validator):
    res = validator.validate({"files": [{"path": "Hello.java", "content": "public class World {}"}]})
    assert res["score"] < 1.0
    assert any("filename" in err for err in res["errors"])

def test_springboot_missing_package(validator):
    res = validator.validate({
        "language": "springboot",
        "files": [{"path": "Hello.java", "content": "public class Hello {}"}]
    })
    assert any("package" in err for err in res["errors"])

def test_validate_security_warning_password(validator):
    res = validator.validate({"files": [{"path": "config.py", "content": "password = 'secret_pass'"}]})
    assert any("security" in err.lower() for err in res["errors"])

@pytest.mark.parametrize("idx, code, expected_grade", [
    (1, "def run():\n    pass", "A"),
    (2, "def run(:\n    pass", "C"),
    (3, "password = '123'", "B"),
    (4, "password = '123'\nsecret = 'xyz'", "B"),
    (5, "public class Sample {}", "B"),
    (6, "public class Test {}", "B"),
    (7, "class Dummy {}", "B"),
    (8, "def f():\n  x = 1\n  y = 2", "A"),
    (9, "def f():\n  return", "A"),
    (10, "const x = 5;", "A"),
    (11, "let y = 10;", "A"),
])
def test_validator_grades(validator, idx, code, expected_grade):
    res = validator.validate({"files": [{"path": "test.py" if "def" in code or "password" in code else "test.js", "content": code}]})
    assert "grade" in res
