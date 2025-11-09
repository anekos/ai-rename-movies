.PHONY: check
check:
	uv run pre-commit run --all-files


.PHONY: test
test:
	uv run pytest
