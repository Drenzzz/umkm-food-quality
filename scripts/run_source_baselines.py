from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


SOURCE_EXPERIMENTS = [
    "exp_001_industry_biscuit_only",
    "exp_002_taterdat_chip_only",
    "exp_003_pepsico_only",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run train, evaluate, and threshold review for source-based public baselines.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path.",
    )
    parser.add_argument(
        "--feature-epochs",
        type=int,
        default=1,
        help="Feature extraction epochs for each experiment.",
    )
    parser.add_argument(
        "--finetune-epochs",
        type=int,
        default=1,
        help="Fine-tuning epochs for each experiment.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for training and evaluation.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project_root = args.project_root.resolve()
    ml_runner = project_root / "scripts" / "run_ml_python.sh"

    for experiment_name in SOURCE_EXPERIMENTS:
        run_command(
            [
                str(ml_runner),
                "ml/train.py",
                "--experiment",
                experiment_name,
                "--feature-epochs",
                str(args.feature_epochs),
                "--finetune-epochs",
                str(args.finetune_epochs),
                "--batch-size",
                str(args.batch_size),
            ],
            project_root,
        )
        run_command([str(ml_runner), "ml/evaluate.py", "--experiment", experiment_name], project_root)
        run_command([str(ml_runner), "ml/review_threshold.py", "--experiment", experiment_name], project_root)
        run_command([str(ml_runner), "scripts/refresh_artifact_manifest.py", "--experiment", experiment_name], project_root)

    results_path = project_root / "docs" / "public_baseline_results.md"
    results_path.write_text(build_results_markdown(project_root), encoding="utf-8")

    summary_path = project_root / "ml" / "model" / "source_baseline_summary.json"
    summary_path.write_text(json.dumps(load_summary(project_root), indent=2), encoding="utf-8")

    print(f"Results updated: {results_path}")
    print(f"Summary written: {summary_path}")
    return 0


def run_command(command: list[str], cwd: Path) -> None:
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def load_summary(project_root: Path) -> dict[str, dict[str, object]]:
    summary = {}
    model_root = project_root / "ml" / "model"
    for experiment_name in SOURCE_EXPERIMENTS:
        evaluation_report = json.loads((model_root / experiment_name / "evaluation" / "evaluation_report.json").read_text(encoding="utf-8"))
        threshold_report = json.loads((model_root / experiment_name / "evaluation" / "threshold_review.json").read_text(encoding="utf-8"))
        summary[experiment_name] = {
            "used_split": evaluation_report["used_split"],
            "accuracy": round(evaluation_report["metrics"]["accuracy"], 4),
            "precision_macro": round(evaluation_report["metrics"]["precision_macro"], 4),
            "recall_macro": round(evaluation_report["metrics"]["recall_macro"], 4),
            "f1_macro": round(evaluation_report["metrics"]["f1_macro"], 4),
            "recall_tidak_layak_jual": round(evaluation_report["metrics"]["recall_tidak_layak_jual"], 4),
            "recommended_threshold": round(threshold_report["recommended_threshold"]["threshold"], 2),
        }
    return summary


def build_results_markdown(project_root: Path) -> str:
    summary = load_summary(project_root)
    lines = [
        "# Public Baseline Results",
        "",
        "Dokumen ini merangkum hasil baseline utama per sumber dataset publik.",
        "",
        "## Experiments",
        "",
        "| Experiment | Source Scope | Status |",
        "|---|---|---|",
        "| `exp_001_industry_biscuit_only` | `industry_biscuit` | completed |",
        "| `exp_002_taterdat_chip_only` | `taterdat_chip` | completed |",
        "| `exp_003_pepsico_only` | `pepsico_potato_lab` | completed |",
        "",
        "## Metrics Snapshot",
        "",
        "| Experiment | Used Split | Accuracy | Precision Macro | Recall Macro | F1 Macro | Recall Tidak Layak Jual | Recommended Threshold |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]

    for experiment_name in SOURCE_EXPERIMENTS:
        item = summary[experiment_name]
        lines.append(
            f"| `{experiment_name}` | `{item['used_split']}` | {item['accuracy']:.4f} | {item['precision_macro']:.4f} | {item['recall_macro']:.4f} | {item['f1_macro']:.4f} | {item['recall_tidak_layak_jual']:.4f} | {item['recommended_threshold']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `industry_biscuit` saat ini menjadi baseline paling aman untuk domain `biskuit_kukis` jika recall `tidak_layak_jual` dijadikan prioritas utama.",
            "- `taterdat_chip` dan `pepsico_potato_lab` tetap menjadi baseline penting untuk domain `keripik`, tetapi hasil akhir harus dibaca bersama eksperimen gabungan keripik berikutnya.",
            "- Ketiga eksperimen utama menghasilkan artefak lengkap: model, class indices, training history, training log, evaluation report, confusion matrix, threshold review, dan artifact manifest.",
            "- Hasil ini masih baseline publik dan belum memasukkan data primer lokal dari Google Form, manual collection, atau scraping tambahan.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
