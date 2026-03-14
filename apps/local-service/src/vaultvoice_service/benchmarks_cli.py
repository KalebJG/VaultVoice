from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vaultvoice_service.models import TranscriptResult
from vaultvoice_service.service import LocalTranscriptionService


@dataclass
class BenchmarkCase:
    case_id: str
    condition: str
    reference: str
    hypothesis: str
    duration_ms: int
    inference_delay_ms: int


class ManifestProvider:
    def __init__(self, manifest_cases: list[BenchmarkCase]) -> None:
        self._cases = {case.case_id: case for case in manifest_cases}
        self._session_order = [case.case_id for case in manifest_cases]
        self._next_session_index = 0

    def start_session(self) -> str:
        if self._next_session_index >= len(self._session_order):
            raise RuntimeError("No benchmark sessions remaining in manifest order.")
        session_id = self._session_order[self._next_session_index]
        self._next_session_index += 1
        return session_id

    def transcribe_chunk(self, session_id: str, pcm_chunk: bytes) -> TranscriptResult:
        _ = (session_id, pcm_chunk)
        return TranscriptResult(text="", is_final=False, confidence=1.0)

    def finalize_session(self, session_id: str) -> TranscriptResult:
        case = self._cases[session_id]
        time.sleep(case.inference_delay_ms / 1000)
        return TranscriptResult(text=case.hypothesis, is_final=True, confidence=1.0)


def _tokenize(text: str) -> list[str]:
    return text.lower().replace("-", " ").split()


def _wer(reference: str, hypothesis: str) -> float:
    ref_words = _tokenize(reference)
    hyp_words = _tokenize(hypothesis)

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    dp = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        dp[i][0] = i
    for j in range(len(hyp_words) + 1):
        dp[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

    return dp[-1][-1] / len(ref_words)


def _load_manifest(path: Path) -> list[BenchmarkCase]:
    raw = json.loads(path.read_text())
    return [
        BenchmarkCase(
            case_id=case["id"],
            condition=case["condition"],
            reference=case["reference"],
            hypothesis=case["hypothesis"],
            duration_ms=case["duration_ms"],
            inference_delay_ms=case["inference_delay_ms"],
        )
        for case in raw["cases"]
    ]


def run(manifest_path: Path) -> dict[str, Any]:
    cases = _load_manifest(manifest_path)
    provider = ManifestProvider(cases)
    service = LocalTranscriptionService(provider=provider)

    case_results: list[dict[str, Any]] = []

    for case in cases:
        start = time.perf_counter()
        session_id = service.start()
        result = service.finalize(session_id)
        elapsed_ms = (time.perf_counter() - start) * 1000

        case_results.append(
            {
                "id": case.case_id,
                "condition": case.condition,
                "reference": case.reference,
                "hypothesis": result.text,
                "duration_ms": case.duration_ms,
                "latency_ms": round(elapsed_ms, 2),
                "rtf": round(elapsed_ms / case.duration_ms, 3),
                "wer": round(_wer(case.reference, result.text), 4),
            }
        )

    latency_values = sorted(r["latency_ms"] for r in case_results)
    p95_index = max(0, min(len(latency_values) - 1, math.ceil(len(latency_values) * 0.95) - 1))

    aggregate = {
        "total_cases": len(case_results),
        "avg_wer": round(statistics.mean(r["wer"] for r in case_results), 4),
        "p95_latency_ms": round(latency_values[p95_index], 2),
        "avg_rtf": round(statistics.mean(r["rtf"] for r in case_results), 3),
    }

    by_condition: dict[str, dict[str, float]] = {}
    for condition in {r["condition"] for r in case_results}:
        rows = [r for r in case_results if r["condition"] == condition]
        by_condition[condition] = {
            "avg_wer": round(statistics.mean(r["wer"] for r in rows), 4),
            "avg_latency_ms": round(statistics.mean(r["latency_ms"] for r in rows), 2),
            "avg_rtf": round(statistics.mean(r["rtf"] for r in rows), 3),
        }

    return {
        "manifest": str(manifest_path),
        "aggregate": aggregate,
        "by_condition": by_condition,
        "cases": case_results,
    }


def _default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "benchmarks" / "dataset_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VaultVoice synthetic STT benchmark harness.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest_path(),
        help="Path to benchmark dataset manifest.",
    )
    parser.add_argument("--output", type=Path, help="Optional path to write JSON results.")
    args = parser.parse_args()

    results = run(args.manifest)
    rendered = json.dumps(results, indent=2)

    if args.output:
        args.output.write_text(rendered + "\n")

    print(rendered)


if __name__ == "__main__":
    main()
