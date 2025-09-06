# Proof Packet Scaffold (Repo B)

A tiny, runnable repo that proves your engine is deterministic, correct, and safe. Paste this into a new repo named `ai-organism-proof-packet/`.

---

## Folder tree

`ai-organism-proof-packet/
  README.md
  Makefile
  bin/
    pp
  schemas/
    obligation.schema.json
    trace.schema.json
  demos/
    01_grandparent.input.json
    02_plan_meeting.input.json
    03_ambiguous_dana.input.json
    04_guardrails.input.json
    05_truncated.input.json
  golden/               # fill after first good run
  runs/                 # produced on execution
  config/
    packet.yaml         # engine URL + compare options`

---

## README.md

````md
# Proof Packet

Run five deterministic demos against your engine, verify byte-for-byte traces, and print basic performance.

## Prereqs
- Python 3.10+
- Your engine (Repo A) running at `http://127.0.0.1:8000`
- Copy the exact JSON Schemas from Repo A into `schemas/`

## Quick start
```bash
make demo      # run the five demos, write traces under runs/
make verify    # compare runs/* vs golden/* (byte-for-byte)
make bench N=128  # optional: throughput/latency at concurrency N
````

## First-time setup (establish goldens)

1. Start your engine and seed data (from Repo A):

   ```bash
   python scripts/seed.py
   uvicorn api.server:app --host 127.0.0.1 --port 8000
   ```
2. Run the demos:

   ```bash
   make demo
   ```
3. Inspect `runs/*.json` and, when satisfied, copy them as goldens:

   ```bash
   cp runs/*.json golden/
   ```
4. Now `make verify` must pass **byte-for-byte** on future runs.

## Notes

* Timestamps or host-specific fields should not be in the trace. If present, either remove them from the engine trace or list them under `ignore_fields` in `config/packet.yaml` so they’re zeroed before compare.

````

---

## Makefile
```make
PY?=python
PP?=bin/pp
DEMO_FILES=$(shell ls demos/*.json)

.PHONY: demo verify bench clean

demo:
	@$(PP) run $(DEMO_FILES) --out runs/

verify:
	@$(PP) verify runs/ golden/

bench:
	@$(PP) bench --concurrency $(N)

clean:
	rm -rf runs/*
````

---

## config/packet.yaml

```yaml
engine_url: "http://127.0.0.1:8000"
schemas:
  obligation: "schemas/obligation.schema.json"
  trace: "schemas/trace.schema.json"
compare:
  ignore_fields: []   # e.g., ["meta.timestamp"] if needed
```

---

## bin/pp (Python CLI runner)

```python
#!/usr/bin/env python
import argparse, os, sys, json, time, hashlib, concurrent.futures as cf
from pathlib import Path
import requests
try:
    from jsonschema import validate
except Exception:
    validate = None

CONFIG = {
    "engine_url": "http://127.0.0.1:8000",
    "schemas": {
        "obligation": "schemas/obligation.schema.json",
        "trace": "schemas/trace.schema.json",
    },
    "compare": {"ignore_fields": []}
}

# --- utils ---

def load_config():
    p = Path("config/packet.yaml")
    if p.exists():
        import yaml
        data = yaml.safe_load(p.read_text())
        # shallow merge
        for k, v in data.items():
            if isinstance(v, dict) and k in CONFIG:
                CONFIG[k].update(v)
            else:
                CONFIG[k] = v


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def strip_ignored_fields(obj, ignore_paths):
    # Supports simple dot-paths like a.b.c
    for path in ignore_paths:
        parts = path.split('.')
        cur = obj
        for i, part in enumerate(parts):
            if isinstance(cur, dict) and part in cur:
                if i == len(parts) - 1:
                    cur[part] = None
                else:
                    cur = cur[part]
            else:
                break
    return obj


def post_execute(obligation_json):
    url = CONFIG["engine_url"].rstrip('/') + "/v1/obligations/execute"
    r = requests.post(url, json=obligation_json, timeout=30)
    r.raise_for_status()
    return r.json()


def validate_json(instance, schema_path):
    if validate is None:
        return True
    import json
    from jsonschema import validate as _validate
    schema = json.load(open(schema_path, 'r', encoding='utf-8'))
    _validate(instance=instance, schema=schema)
    return True

# --- commands ---

def cmd_run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    load_config()

    successes = 0
    for demo in args.files:
        name = Path(demo).stem
        with open(demo, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        # optional: validate input against schema
        if Path(CONFIG['schemas']['obligation']).exists():
            validate_json(payload, CONFIG['schemas']['obligation'])
        resp = post_execute(payload)
        if Path(CONFIG['schemas']['trace']).exists():
            validate_json(resp, CONFIG['schemas']['trace'])
        # normalize ignored fields
        resp = strip_ignored_fields(resp, CONFIG['compare']['ignore_fields'])
        out_path = out / f"{name}.trace.json"
        out_path.write_text(json.dumps(resp, ensure_ascii=False, separators=(',',':')))
        successes += 1
        print(f"[OK] {name}")
    print(f"Done. {successes}/{len(args.files)} demos written to {out}")


def cmd_verify(args):
    load_config()
    runs, gold = Path(args.runs), Path(args.golden)
    failures = 0
    for run_file in sorted(runs.glob("*.json")) | sorted(runs.glob("*.trace.json")):
        base = run_file.name.replace('.trace.json','').replace('.json','')
        gold_file = (gold / f"{base}.trace.json")
        if not gold_file.exists():
            print(f"[MISS] golden not found for {base}")
            failures += 1
            continue
        rb = run_file.read_bytes()
        gb = gold_file.read_bytes()
        # hashes
        rh, gh = sha256_bytes(rb), sha256_bytes(gb)
        if rh != gh:
            print(f"[DIFF] {base}: run={rh} gold={gh}")
            failures += 1
        else:
            print(f"[OK]   {base}")
    if failures:
        print(f"FAIL: {failures} mismatches"); sys.exit(1)
    print("All traces match goldens.")


def cmd_bench(args):
    load_config()
    demo_files = sorted(Path('demos').glob('*.json'))
    if not demo_files:
        print('No demos found.'); sys.exit(2)

    def one(name_payload):
        name, payload = name_payload
        t0 = time.perf_counter()
        _ = post_execute(payload)
        return (name, (time.perf_counter()-t0)*1000.0)

    batch = [(p.stem, json.loads(Path(p).read_text())) for p in demo_files]
    latencies = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(one, item) for item in batch*max(1, args.repeat)]
        for fut in cf.as_completed(futs):
            _, ms = fut.result()
            latencies.append(ms)
    latencies.sort()
    def pct(p):
        k = int((p/100.0)*(len(latencies)-1))
        return latencies[k]
    p50, p95 = pct(50), pct(95)
    print(json.dumps({"concurrency": args.concurrency, "repeat": args.repeat, "p50_ms": p50, "p95_ms": p95, "n": len(latencies)}, indent=2))


def main():
    ap = argparse.ArgumentParser(prog='pp', description='Proof Packet runner')
    sub = ap.add_subparsers(dest='cmd', required=True)

    ap_run = sub.add_parser('run');
    ap_run.add_argument('files', nargs='+', help='demo input JSON files')
    ap_run.add_argument('--out', default='runs/', help='output folder')
    ap_run.set_defaults(func=cmd_run)

    ap_verify = sub.add_parser('verify');
    ap_verify.add_argument('runs'); ap_verify.add_argument('golden')
    ap_verify.set_defaults(func=cmd_verify)

    ap_bench = sub.add_parser('bench');
    ap_bench.add_argument('--concurrency', type=int, default=32)
    ap_bench.add_argument('--repeat', type=int, default=4)
    ap_bench.set_defaults(func=cmd_bench)

    args = ap.parse_args(); args.func(args)

if __name__ == '__main__':
    main()
```

> After saving, make it executable: `chmod +x bin/pp` (PowerShell: call via `python bin/pp ...`).

---

## schemas/\*

Copy the exact `obligation.schema.json` and `trace.schema.json` from Repo A (pin the versions you used for current green tests).

---

## Demo inputs (demos/\*.json)

> These match your current engine tests. Adjust times/IDs if needed.

### 01\_grandparent.input.json

```json
{
  "obligations": [
    {"type": "REPORT", "payload": {
      "kind":"logic", "mode":"deduction", "domains":["kinship"],
      "query": {"predicate":"grandparentOf","args":["Alice","Cara"]},
      "facts": [
        {"predicate":"parentOf","args":["Alice","Bob"]},
        {"predicate":"parentOf","args":["Bob","Cara"]}
      ],
      "budgets": {"max_depth":3, "beam":4, "time_ms":100}
    }}
  ]
}
```

### 02\_plan\_meeting.input.json

```json
{
  "obligations": [
    {"type": "ACHIEVE", "payload": {
      "state":"plan", "kind":"plan", "mode":"planning",
      "goal": {"predicate":"event.scheduled","args":{"person":"Dana","time":"2025-09-06T13:00-07:00"}},
      "budgets": {"max_depth":3, "beam":3, "time_ms":150}
    }}
  ]
}
```

### 03\_ambiguous\_dana.input.json

```json
{
  "obligations": [
    {"type": "ACHIEVE", "payload": {
      "state":"plan", "kind":"plan", "mode":"planning",
      "goal": {"predicate":"event.scheduled","args":{"person":"Dana","time":"2025-09-06T13:00-07:00"}},
      "budgets": {"max_depth":3, "beam":3, "time_ms":150},
      "simulate_ambiguous": true
    }}
  ]
}
```

### 04\_guardrails.input.json

```json
{
  "obligations": [
    {"type": "ACHIEVE", "payload": {
      "state":"plan", "kind":"plan", "mode":"planning",
      "goal": {"predicate":"event.scheduled","args":{"person":"Dana","time":"2025-09-06T13:00-07:00"}},
      "guardrails": [
        {"type":"MAINTAIN", "predicate":"calendar.free", "args":["Dana", {"start":"2025-09-06T09:00-07:00","end":"2025-09-06T17:00-07:00"}]},
        {"type":"AVOID", "predicate":"double_book", "args":["Dana","2025-09-06T13:00-07:00"]}
      ],
      "budgets": {"max_depth":3, "beam":3, "time_ms":150}
    }}
  ]
}
```

### 05\_truncated.input.json

```json
{
  "obligations": [
    {"type": "REPORT", "payload": {
      "kind":"logic", "mode":"deduction", "domains":["kinship"],
      "query": {"predicate":"grandparentOf","args":["Alice","Cara"]},
      "facts": [
        {"predicate":"parentOf","args":["Alice","Bob"]},
        {"predicate":"parentOf","args":["Bob","Cara"]}
      ],
      "budgets": {"max_depth":1, "beam":1, "time_ms":1}
    }}
  ]
}
```

---

## How to create goldens

1. Start the engine and seed as usual.
2. Run `make demo`.
3. Inspect `runs/*.trace.json` to ensure:

   * no timestamps/host-specific fields
   * routing order is deterministic
   * planning writes **no** side effects
4. Copy to `golden/`:

   ```bash
   cp runs/*.trace.json golden/
   ```
5. Verify determinism:

   ```bash
   make verify
   ```

---

## Tips

* If traces include transient fields you can’t remove yet, list them in `config/packet.yaml: compare.ignore_fields` and the runner will null them before hashing/compare.
* On Windows/PowerShell: run the CLI via `python bin/pp run demos/*.json --out runs/`.
* Keep this repo dependency-free beyond `requests` (and `jsonschema` optionally).

```
```
