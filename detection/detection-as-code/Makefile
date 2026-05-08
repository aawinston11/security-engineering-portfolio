.PHONY: setup lint validate purple-team navigator convert test all clean

UV ?= uv

setup:
	$(UV) sync --extra dev

lint:
	$(UV) run python -m detection_as_code.cli lint

validate: lint
	$(UV) run python -m detection_as_code.cli validate-attack-mappings

purple-team:
	$(UV) run python -m detection_as_code.cli purple-team

navigator:
	$(UV) run python -m detection_as_code.cli navigator

convert:
	$(UV) run python -m detection_as_code.cli convert-spl

test:
	$(UV) run pytest -v

all: lint validate purple-team

clean:
	rm -rf .venv .pytest_cache .ruff_cache build generated-spl
