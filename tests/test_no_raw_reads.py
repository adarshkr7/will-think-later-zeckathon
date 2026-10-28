import ast
from pathlib import Path


def test_no_indian_input_reads_in_features_or_models(config):
    for folder in ("features", "models", "policy"):
        for path in (config.root / "prahari" / folder).glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    assert node.attr not in {"read_csv", "read_parquet", "read_excel", "read_json"}, str(path)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert "data/manual" not in node.value and "data/raw" not in node.value, str(path)


def test_no_llm_calls_in_pipeline(config):
    for path in (config.root / "prahari").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any(alias.name.split(".")[0] in {"openai", "anthropic", "google.generativeai"} for alias in node.names)
