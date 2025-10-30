# Dependency Analysis Report

This report summarizes the findings of a dependency analysis performed on the codebase.

## Circular Dependencies

No circular dependencies were found using `pydeps`.

## Unused Dependencies

The following dependencies are defined in `pyproject.toml` but are not detected as being used in the codebase. These are candidates for removal.

- `psycopg2-binary`
- `openpyxl`
- `python-multipart`
- `passlib`
- `python-jose`
- `aiosqlite`
- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-mock`
- `factory-boy`
- `faker`
- `black`
- `isort`
- `flake8`
- `mypy`
- `ruff`
- `scikit-learn`
- `scipy`

## Missing Dependencies

The following modules are imported in the code but are not explicitly defined as dependencies in `pyproject.toml`.

- `utils`
- `config`
- `db`
- `shopify`
- `stockx_real`
- `stockx`
- `awin`
- `security`
- `shared`
- `domains`
- `sklearn`
- `services`
- `aiohttp`
- `sync_notion_to_postgres`
- `brotli`
- `aiofiles`
- `stripe`

*Note: `shared` and `domains` appear to be local packages and likely do not need to be added to `pyproject.toml`.*

## Transitive Dependencies

The following dependencies are used in the code but are installed as dependencies of other dependencies. It is recommended to add them to `pyproject.toml` to make the dependency explicit.

- `urllib3`
- `numpy`
- `starlette`
- `dateutil`
- `typing_extensions`
