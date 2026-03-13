# STT Baseline (MVP T2.4)

This baseline is produced by the local benchmark harness in `apps/local-service/benchmarks`.

## Scope
- Short-form dictation utterances.
- Two acoustic conditions: `clean` and `moderate_noise`.
- CPU-only local-service execution path.
- Current harness uses a deterministic synthetic provider output so teams can validate reproducible WER/latency math and reporting while full STT integration is pending.

## How to reproduce
```bash
python apps/local-service/benchmarks/run_benchmark.py \
  --manifest apps/local-service/benchmarks/dataset_manifest.json \
  --output apps/local-service/benchmarks/baseline_results.json
```

## Baseline summary
From `apps/local-service/benchmarks/baseline_results.json`:

- Total cases: `4`
- Average WER: `0.0903`
- P95 latency: `115.17 ms`
- Average real-time factor (RTF): `0.07`

### Condition breakdown
| Condition | Avg WER | Avg Latency (ms) | Avg RTF |
| --- | ---: | ---: | ---: |
| clean | 0.0625 | 77.69 | 0.059 |
| moderate_noise | 0.1181 | 112.69 | 0.081 |

## Notes
- This benchmark is intended as an MVP harness and reporting baseline; it is not yet representative of production model quality.
- Once the real transcription provider is integrated, keep this harness and swap provider wiring so this document can track real WER/latency progression over time.
