"""Entry point: `python -m eval.run [--config NAME ...]` (from backend/, or the Compose profile).

Reads the same environment as the API (`load_settings`), applies each configuration's overrides
and writes one report per configuration plus `comparison.md` to the output directory.
"""

import argparse
import asyncio
from pathlib import Path

from app.config import Settings, load_settings
from eval.dataset import Dataset, EvalConfig, EvalPlan, load_dataset, load_plan
from eval.report import write_comparison, write_run
from eval.runner import RunResult, build_eval_container, configured_settings, evaluate

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m eval.run", description=__doc__)
    parser.add_argument("--dataset", type=Path, default=BACKEND_DIR / "eval/dataset.yaml")
    parser.add_argument("--plan", type=Path, default=BACKEND_DIR / "eval/configs.yaml")
    parser.add_argument("--documents", type=Path, default=BACKEND_DIR / "tests/fixtures/documents")
    parser.add_argument("--out", type=Path, default=BACKEND_DIR.parent / "docs/eval")
    parser.add_argument(
        "--config", action="append", help="run only this configuration (repeatable)"
    )
    return parser.parse_args(argv)


def _selected(plan: EvalPlan, names: list[str] | None) -> list[EvalConfig]:
    if not names:
        return plan.configurations
    known = {config.name: config for config in plan.configurations}
    unknown = sorted(set(names) - known.keys())
    if unknown:
        raise SystemExit(f"Unknown configuration(s): {', '.join(unknown)}")
    return [known[name] for name in names]


async def _run_one(
    base: Settings, config: EvalConfig, dataset: Dataset, plan: EvalPlan, documents: Path
) -> RunResult:
    container, recorder = build_eval_container(configured_settings(base, config))
    try:
        return await evaluate(container, recorder, dataset, plan, config, documents)
    finally:
        await container.engine.dispose()


async def _main(args: argparse.Namespace) -> None:
    dataset, plan = load_dataset(args.dataset), load_plan(args.plan)
    configs = _selected(plan, args.config)
    base = load_settings()
    results = []
    for config in configs:
        print(f"Running {config.name} ({len(dataset.questions)} questions)...", flush=True)
        result = await _run_one(base, config, dataset, plan, args.documents)
        write_run(result, args.out)
        results.append(result)
        s = result.summary
        print(
            f"  hit@k {s.mean_hit_at_k}, refusal {s.refusal_rate}, "
            f"citations {s.citation_validity}, errors {s.errors}",
            flush=True,
        )
    if any(result.partial_collection for result in results):
        print("Warning: not every document is Ready; see the Documents table.", flush=True)
    if len(results) > 1:
        write_comparison(results, args.out)
    else:  # a single configuration does not rewrite comparison.md, which may now be stale
        print("comparison.md not rewritten: run every configuration to refresh it.", flush=True)
    print(f"Reports written to {args.out}")


def main(argv: list[str] | None = None) -> None:
    asyncio.run(_main(_arguments(argv)))


if __name__ == "__main__":
    main()
