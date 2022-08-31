
# Otodom Flat monitoring

This job

* Fetches flats with specified filters (see `__main__.py`)
* Logs them as JSON and writes found flats to SQLite DB.
* Reports newly found flats to Telegram channel.

## Run

To run this bot, simply do

```bash
docker run \
  -v <some-local-path>:/opt/data \
  ivanychev/otodom:0.1 \
  python -m otodom --bot-token=<bot-token> --data-path=/opt/data
```

## Deploy new version

1. Increase the version in `build_docker.sh`
2. Run the `build_docker.sh` (this builds and pushes a Docker image).
3. Use an example from `crontab.txt` to set up a regular job on a Linux machine.

## Set up development environment.

1. Install Python 3.10 and Poetry (`brew install poetry` if on macOS or as [written here](https://python-poetry.org/docs/#installation))
2. Create a virtual environment `python -m venv venv`
3. Activate the environment `source venv/bin/activate`
4. Install the dependencies `poetry install --no-root`
5. Have fun!

## Format the code

```bash
make format
```