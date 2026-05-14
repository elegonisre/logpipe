# logpipe

Minimal log aggregator that tails multiple files and forwards structured events to a sink.

---

## Installation

```bash
pip install logpipe
```

Or install from source:

```bash
git clone https://github.com/yourname/logpipe.git && cd logpipe && pip install .
```

---

## Usage

Define your sources and sink in a config file (`logpipe.yaml`):

```yaml
sources:
  - path: /var/log/app/api.log
    format: json
  - path: /var/log/app/worker.log
    format: json

sink:
  type: http
  url: https://logs.example.com/ingest
  headers:
    Authorization: Bearer YOUR_TOKEN
```

Then run:

```bash
logpipe --config logpipe.yaml
```

You can also pipe output directly to stdout for debugging:

```bash
logpipe --config logpipe.yaml --sink stdout
```

**Programmatic usage:**

```python
from logpipe import Pipeline

pipeline = Pipeline(sources=["/var/log/app/api.log"], sink="stdout")
pipeline.run()
```

---

## Features

- Tails multiple log files concurrently
- Parses and forwards structured (JSON) events
- Pluggable sinks: HTTP, stdout, file
- Lightweight with no heavy dependencies

---

## License

MIT © 2024 yourname