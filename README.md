
# Otodom Flat monitoring

This job

* Fetches flats with specified filters (see `__main__.py`)
* Logs them as JSON and writes found flats to SQLite DB.
* Reports newly found flats to Telegram channel.


To run this bot, simply do

```bash
docker run \
  -v <some-local-path>:/opt/data \
  ivanychev/otodom:0.1 \
  python -m otodom --bot-token=<bot-token> --data-path=/opt/data
```