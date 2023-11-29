from setuptools import setup

setup(
    name="orch",
    version="0.1",
    description="A postgres based orchestrator proof of concept",
    python_requires=">=3.10",
    package_dir={"": "src"},
    install_requires=[
        "aiostream == 0.5.2",
        "alembic == 1.12.1",
        "asyncpg == 0.29.0",
        "cachetools == 4.2.4",
        "fastapi == 0.104.1",
        "fastapi-utils @ git+https://github.com/dmontagu/fastapi-utils.git#egg=fastapi-utils",
        "httpx == 0.25.2",
        "loguru == 0.7.2",
        "psycopg2-binary == 2.9.9",
        "pydantic",
        "python-dateutil == 2.8.2",
        "python-dotenv == 1.0.0",
        "sqlalchemy == 1.4.50",
        "uvicorn == 0.24.0",
        "typing_extensions",
    ],
)
