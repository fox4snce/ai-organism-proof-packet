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
```

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
4. Now `make verify` must pass byte-for-byte on future runs.

## Notes

* Timestamps or host-specific fields should not be in the trace. If present, either remove them from the engine trace or list them under `ignore_fields` in `config/packet.yaml` so they’re zeroed before compare.

