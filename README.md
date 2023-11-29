# orch

An orchestrator prototype, built on top of postgres

## configure

Link or copy and edit the config file
```shell
ln -s env.default .env
```

## install and run via docker (recommended)

```shell
docker-compose up --build
```

## install and run manually

Install orch:
```shell
python -m pip install --user -e .
```

Migrate the database:
```shell
alembic upgrade head
```

Run the API listening on port 8000:
```shell
uvicorn orch:app
```

## Running

Run example flow:
```shell
curl --request POST \
  --url http://localhost:8000/flows \
  --header 'Content-Type: application/json' \
  --data '{
        "name": "example",
        "args": {
                "wait_time": 10
        }
}' | jq
```

Retrieve executed flows:
```shell
curl --request GET --url http://localhost:8000/flows | jq
```
