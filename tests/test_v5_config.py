import os
import pytest
from backend.shared.config_loader import ConfigLoader, get_config
from backend.shared.prompt_loader import PromptLoader, get_prompt_loader

def test_config_loader():
    ConfigLoader.reset()
    cfg = ConfigLoader.get_instance()
    
    # Check default keys
    assert cfg.get("app.name") == "MSA AI Agent V5.0"
    assert cfg.get("server.fastapi_port") == 8000
    
    # Check feature flags
    assert cfg.feature("enable_kafka") is False
    assert cfg.feature("enable_speech") is True
    
    # Check model routing
    model_cfg = cfg.get_model_config("CODING")
    assert model_cfg is not None
    assert "primary" in model_cfg
    
    # Check persona loading
    persona = cfg.get_persona("developer")
    assert persona is not None
    assert persona["display_name"] == "Senior Developer"

def test_prompt_loader(tmp_path):
    # Create temp prompts directory
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    
    test_prompt = prompts_dir / "test_prompt.md"
    test_prompt.write_text("Hello {{name}}, welcome to {{system}}!", encoding="utf-8")
    
    loader = PromptLoader(prompts_dir=prompts_dir)
    raw = loader.get("test_prompt")
    assert raw == "Hello {{name}}, welcome to {{system}}!"
    
    rendered = loader.render("test_prompt", name="Alice", system="MSA OS")
    assert rendered == "Hello Alice, welcome to MSA OS!"
