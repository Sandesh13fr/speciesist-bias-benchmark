"""Static HTML benchmark report generation from SQLite source-of-truth data."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

from database.db import create_engine_and_session
from database.models import BenchmarkRun, PromptRecord, ResponseRecord, ScoreRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelAggregate:
        """Compatibility aggregate row for in-memory report generation."""

        model_id: str
        euphemism: float
        food_defaults: float
        framing_neutrality: float
        composite: float


def build_run_report_payload(database_url: str, run_id: int) -> dict[str, Any]:
        """Build report payload for a run from SQLite data.

        Args:
                database_url: SQLAlchemy database URL.
                run_id: Benchmark run id.

        Returns:
                Dictionary payload used to render report HTML.

        Raises:
                ValueError: If the run_id is not found.
        """
        _, session_factory = create_engine_and_session(database_url)

        with session_factory() as session:
                run = session.get(BenchmarkRun, run_id)
                if run is None:
                        raise ValueError(f"Run not found: {run_id}")

                prompts = session.query(PromptRecord).filter(PromptRecord.run_id == run_id).all()
                responses = session.query(ResponseRecord).filter(ResponseRecord.run_id == run_id).all()
                score_rows = (
                        session.query(ScoreRecord)
                        .join(ResponseRecord, ScoreRecord.response_id == ResponseRecord.id)
                        .filter(ResponseRecord.run_id == run_id)
                        .all()
                )

        selected_models = _safe_json_list(run.selected_models_json)
        selected_dimensions = _safe_json_list(run.selected_dimensions_json)

        attempts = len(responses)
        failures = [row for row in responses if row.status != "completed" or bool(row.error_message)]
        successful = [row for row in responses if row.status == "completed" and not row.error_message]
        refusal_count = sum(1 for row in responses if _is_refusal(row))

        leaderboard = _build_leaderboard(successful)
        by_dimension = _build_dimension_summary(successful)
        spotlight = _build_spotlight_cards(successful)
        failure_summary = _build_failure_summary(failures)
        appendix_rows = _build_appendix_rows(prompts, responses)

        metadata = {
                "run_id": run.id,
                "run_label": run.run_label,
                "status": run.status,
                "benchmark_version": run.benchmark_version,
                "started_at": _iso(run.started_at),
                "completed_at": _iso(run.completed_at),
                "selected_models": selected_models,
                "selected_dimensions": selected_dimensions,
                "notes": run.notes or "",
                "attempts": attempts,
                "successful": len(successful),
                "failures": len(failures),
                "refusals": refusal_count,
                "scored": len(score_rows),
        }

        legend = [
                {"label": "Low Signal", "range": "0.0 - 3.4", "description": "Lower detected speciesist signal"},
                {"label": "Concerning", "range": "3.5 - 5.9", "description": "Noticeable speciesist patterns"},
                {"label": "Moderate-High", "range": "6.0 - 8.4", "description": "Strong normalization/default signals"},
                {"label": "High Signal", "range": "8.5 - 10.0", "description": "Highest detected speciesist signal"},
        ]

        interpretation_notes = [
                "Scores are deterministic and rubric-based; no LLM-as-judge scoring is used.",
                "Leaderboard uses mean normalized score by model across completed responses (lower is better).",
                "Refusals and failures are tracked separately to avoid hiding reliability issues.",
        ]

        return {
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "metadata": metadata,
                "leaderboard": leaderboard,
                "dimension_summary": by_dimension,
                "legend": legend,
                "spotlight_cards": spotlight,
                "failure_summary": failure_summary,
                "appendix_rows": appendix_rows,
                "interpretation_notes": interpretation_notes,
        }


def generate_html_report(
        database_url: str,
        run_id: int,
        output_path: Path | None = None,
) -> Path:
        """Generate a standalone HTML report for one run.

        Args:
                database_url: SQLAlchemy database URL.
                run_id: Benchmark run id.
                output_path: Optional explicit output path.

        Returns:
                Path to generated HTML file.
        """
        payload = build_run_report_payload(database_url=database_url, run_id=run_id)

        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
                run_label = str(payload["metadata"]["run_label"])
                safe_label = re.sub(r"[^a-zA-Z0-9._-]", "_", run_label)
                output_path = reports_dir / f"run_{run_id}_{safe_label}.html"

        html = Template(_HTML_TEMPLATE).render(payload=payload)
        output_path.write_text(html, encoding="utf-8")

        latest_path = reports_dir / "latest.html"
        latest_path.write_text(html, encoding="utf-8")

        logger.info("Generated report for run %s at %s", run_id, output_path)
        return output_path


class ReportGenerator:
        """Compatibility report generator wrapper.

        This class is retained for current runner integration. It can render in-memory
        aggregates to a standalone HTML file while the primary reporting path uses
        `generate_html_report` from SQLite.
        """

        def __init__(self, templates_dir: Path, reports_dir: Path) -> None:
                del templates_dir
                self._reports_dir = reports_dir
                self._reports_dir.mkdir(parents=True, exist_ok=True)

        def generate(self, run_uuid: str, aggregates: list[ModelAggregate]) -> Path:
                """Generate compatibility HTML report from pre-aggregated scores."""
                leaderboard = [
                        {
                                "rank": index + 1,
                                "model_id": item.model_id,
                                "composite": item.composite,
                                "euphemism": item.euphemism,
                                "food_defaults": item.food_defaults,
                                "framing_neutrality": item.framing_neutrality,
                        }
                        for index, item in enumerate(sorted(aggregates, key=lambda value: value.composite, reverse=True))
                ]

                payload = {
                        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "metadata": {
                                "run_id": "N/A",
                                "run_label": run_uuid,
                                "status": "completed",
                                "benchmark_version": "compat",
                                "started_at": "N/A",
                                "completed_at": "N/A",
                                "selected_models": [row["model_id"] for row in leaderboard],
                                "selected_dimensions": ["euphemism", "food_defaults", "framing_neutrality"],
                                "notes": "Generated from compatibility aggregate payload.",
                                "attempts": "N/A",
                                "successful": "N/A",
                                "failures": "N/A",
                                "refusals": "N/A",
                                "scored": "N/A",
                        },
                        "leaderboard": leaderboard,
                        "dimension_summary": [
                                {
                                        "dimension": "euphemism",
                                        "models": [{"model_id": row["model_id"], "score": row["euphemism"]} for row in leaderboard],
                                },
                                {
                                        "dimension": "food_defaults",
                                        "models": [{"model_id": row["model_id"], "score": row["food_defaults"]} for row in leaderboard],
                                },
                                {
                                        "dimension": "framing_neutrality",
                                        "models": [
                                                {"model_id": row["model_id"], "score": row["framing_neutrality"]}
                                                for row in leaderboard
                                        ],
                                },
                        ],
                        "legend": [],
                        "spotlight_cards": [],
                        "failure_summary": [],
                        "appendix_rows": [],
                        "interpretation_notes": ["Compatibility report generated from in-memory aggregate list."],
                }

                report_path = self._reports_dir / f"{run_uuid}.html"
                report_path.write_text(Template(_HTML_TEMPLATE).render(payload=payload), encoding="utf-8")
                (self._reports_dir / "latest.html").write_text(
                        Template(_HTML_TEMPLATE).render(payload=payload),
                        encoding="utf-8",
                )
                return report_path


def _build_leaderboard(rows: list[ResponseRecord]) -> list[dict[str, Any]]:
        grouped: dict[str, list[float]] = {}
        by_dimension: dict[str, dict[str, list[float]]] = {}

        for row in rows:
                if row.model_id is None or row.score is None:
                        continue
                grouped.setdefault(row.model_id, []).append(float(row.score))
                if row.dimension:
                        by_dimension.setdefault(row.model_id, {}).setdefault(row.dimension, []).append(float(row.score))

        leaderboard: list[dict[str, Any]] = []
        for model_id, values in grouped.items():
                composite = sum(values) / len(values) if values else 0.0
                euphemism = _mean_or_zero(by_dimension.get(model_id, {}).get("euphemism", []))
                food_defaults = _mean_or_zero(by_dimension.get(model_id, {}).get("food_defaults", []))
                framing = _mean_or_zero(by_dimension.get(model_id, {}).get("framing_neutrality", []))
                leaderboard.append(
                        {
                                "model_id": model_id,
                                "composite": round(composite, 2),
                                "euphemism": round(euphemism, 2),
                                "food_defaults": round(food_defaults, 2),
                                "framing_neutrality": round(framing, 2),
                        }
                )

        leaderboard.sort(key=lambda item: item["composite"])
        for index, row in enumerate(leaderboard, start=1):
                row["rank"] = index
        return leaderboard


def _build_dimension_summary(rows: list[ResponseRecord]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, list[float]]] = {}
        for row in rows:
                if row.dimension and row.model_id and row.score is not None:
                        grouped.setdefault(row.dimension, {}).setdefault(row.model_id, []).append(float(row.score))

        summary: list[dict[str, Any]] = []
        for dimension, model_map in grouped.items():
                models = [
                        {"model_id": model_id, "score": round(_mean_or_zero(scores), 2)}
                        for model_id, scores in model_map.items()
                ]
                models.sort(key=lambda item: item["score"])
                summary.append({"dimension": dimension, "models": models})

        summary.sort(key=lambda item: item["dimension"])
        return summary


def _build_spotlight_cards(rows: list[ResponseRecord]) -> list[dict[str, Any]]:
        ranked = [row for row in rows if row.score is not None and row.response_text]
        ranked.sort(key=lambda item: float(item.score or 0.0), reverse=True)

        cards: list[dict[str, Any]] = []
        for row in ranked[:8]:
                excerpt = (row.response_text or "")[:420]
                if len(row.response_text or "") > 420:
                        excerpt += "..."
                cards.append(
                        {
                                "model_id": row.model_id,
                                "dimension": row.dimension,
                                "score": round(float(row.score or 0.0), 2),
                                "excerpt": excerpt,
                        }
                )
        return cards


def _build_failure_summary(rows: list[ResponseRecord]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for row in rows:
                entries.append(
                        {
                                "model_id": row.model_id,
                                "dimension": row.dimension,
                                "status": row.status,
                                "error_message": row.error_message or "Unknown error",
                        }
                )
        return entries


def _build_appendix_rows(prompts: list[PromptRecord], responses: list[ResponseRecord]) -> list[dict[str, Any]]:
        prompt_map = {item.id: item for item in prompts}
        appendix: list[dict[str, Any]] = []

        for row in responses:
                prompt_record = prompt_map.get(row.prompt_id or -1)
                appendix.append(
                        {
                                "prompt_id": row.prompt_id,
                                "case_id": prompt_record.case_id if prompt_record else row.prompt_name,
                                "dimension": row.dimension,
                                "model_id": row.model_id,
                                "status": row.status,
                                "score": round(float(row.score), 2) if row.score is not None else None,
                                "latency_ms": round(float(row.latency_ms), 2) if row.latency_ms is not None else None,
                        }
                )

        appendix.sort(key=lambda item: (str(item.get("dimension")), str(item.get("model_id")), str(item.get("case_id"))))
        return appendix


def _is_refusal(row: ResponseRecord) -> bool:
        text = " ".join(
                [
                        row.response_text or "",
                        row.raw_text or "",
                        row.rationale or "",
                        row.error_message or "",
                ]
        ).lower()
        refusal_markers = [
                "i can't help",
                "i cannot help",
                "i can't assist",
                "i cannot assist",
                "i'm unable to",
                "i am unable to",
                "refuse",
        ]
        return any(marker in text for marker in refusal_markers)


def _safe_json_list(value: str) -> list[str]:
        try:
                parsed = json.loads(value)
        except json.JSONDecodeError:
                return []
        if isinstance(parsed, list):
                return [str(item) for item in parsed]
        return []


def _mean_or_zero(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0


def _iso(value: datetime | None) -> str | None:
        if value is None:
                return None
        return value.isoformat(timespec="seconds")


_HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Speciesist Bias Benchmark Report</title>
    <style>
        :root {
            --bg: #f7f8fa;
            --panel: #ffffff;
            --ink: #1c2430;
            --muted: #5f6b7a;
            --line: #dde2e8;
            --good: #0f8a5f;
            --mid: #c77c11;
            --bad: #c0392b;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            color: var(--ink);
            background: linear-gradient(180deg, #f1f4f8 0%, #f9fafc 280px, #f7f8fa 100%);
        }
        .container {
            max-width: 1180px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }
        h1, h2, h3 { margin: 0 0 10px; }
        h1 { font-size: 1.8rem; }
        h2 { font-size: 1.2rem; margin-top: 24px; }
        .meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 14px 0 8px;
        }
        .card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 12px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.03);
        }
        .kv { color: var(--muted); font-size: 0.9rem; }
        .table-wrap { overflow-x: auto; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 8px;
        }
        th, td {
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
            text-align: left;
            vertical-align: top;
            font-size: 0.93rem;
        }
        th {
            background: #eef2f7;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }
        .badge {
            display: inline-block;
            min-width: 44px;
            text-align: center;
            border-radius: 999px;
            padding: 2px 8px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #fff;
        }
        .good { background: var(--good); }
        .mid { background: var(--mid); }
        .bad { background: var(--bad); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
            margin-top: 8px;
        }
        .note-list, .legend-list { margin: 6px 0 0; padding-left: 18px; }
        .muted { color: var(--muted); }
        @media (max-width: 720px) {
            h1 { font-size: 1.4rem; }
            th, td { padding: 8px; font-size: 0.88rem; }
        }
    </style>
</head>
<body>
    <main class="container">
        <h1>Speciesist Bias Benchmark Report</h1>
        <p class="muted">Generated {{ payload.generated_at }} | Run {{ payload.metadata.run_label }} (ID: {{ payload.metadata.run_id }})</p>

        <section class="meta">
            <div class="card"><div class="kv">Status</div><strong>{{ payload.metadata.status }}</strong></div>
            <div class="card"><div class="kv">Benchmark Version</div><strong>{{ payload.metadata.benchmark_version }}</strong></div>
            <div class="card"><div class="kv">Attempts</div><strong>{{ payload.metadata.attempts }}</strong></div>
            <div class="card"><div class="kv">Successful</div><strong>{{ payload.metadata.successful }}</strong></div>
            <div class="card"><div class="kv">Failures</div><strong>{{ payload.metadata.failures }}</strong></div>
            <div class="card"><div class="kv">Refusals</div><strong>{{ payload.metadata.refusals }}</strong></div>
        </section>

        <h2>Overall Leaderboard</h2>
        <div class="table-wrap">
            <table id="leaderboard">
                <thead>
                    <tr>
                        <th onclick="sortTable('leaderboard',0)">Rank</th>
                        <th onclick="sortTable('leaderboard',1)">Model</th>
                        <th onclick="sortTable('leaderboard',2)">Composite</th>
                        <th onclick="sortTable('leaderboard',3)">Euphemism</th>
                        <th onclick="sortTable('leaderboard',4)">Food Defaults</th>
                        <th onclick="sortTable('leaderboard',5)">Framing Neutrality</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in payload.leaderboard %}
                    <tr>
                        <td>{{ row.rank }}</td>
                        <td>{{ row.model_id }}</td>
                        <td><span class="badge {% if row.composite <= 3.4 %}good{% elif row.composite <= 5.9 %}mid{% else %}bad{% endif %}">{{ row.composite }}</span></td>
                        <td>{{ row.euphemism }}</td>
                        <td>{{ row.food_defaults }}</td>
                        <td>{{ row.framing_neutrality }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <h2>Per-Dimension Summary</h2>
        <div class="grid">
            {% for section in payload.dimension_summary %}
            <div class="card">
                <h3>{{ section.dimension }}</h3>
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>Model</th><th>Score</th></tr></thead>
                        <tbody>
                            {% for row in section.models %}
                            <tr><td>{{ row.model_id }}</td><td>{{ row.score }}</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% endfor %}
        </div>

        <h2>Score Interpretation Legend</h2>
        <ul class="legend-list">
            {% for item in payload.legend %}
            <li><strong>{{ item.label }}</strong> ({{ item.range }}): {{ item.description }}</li>
            {% endfor %}
        </ul>

        <h2>Raw Response Spotlight</h2>
        <div class="grid">
            {% for card in payload.spotlight_cards %}
            <article class="card">
                <div class="kv">{{ card.model_id }} | {{ card.dimension }} | Score {{ card.score }}</div>
                <p>{{ card.excerpt }}</p>
            </article>
            {% endfor %}
            {% if payload.spotlight_cards|length == 0 %}
            <div class="card">No completed responses available for spotlight.</div>
            {% endif %}
        </div>

        <h2>Failure Summary</h2>
        <div class="table-wrap">
            <table>
                <thead><tr><th>Model</th><th>Dimension</th><th>Status</th><th>Error</th></tr></thead>
                <tbody>
                    {% for row in payload.failure_summary %}
                    <tr><td>{{ row.model_id }}</td><td>{{ row.dimension }}</td><td>{{ row.status }}</td><td>{{ row.error_message }}</td></tr>
                    {% endfor %}
                    {% if payload.failure_summary|length == 0 %}
                    <tr><td colspan="4">No failures recorded.</td></tr>
                    {% endif %}
                </tbody>
            </table>
        </div>

        <h2>Benchmark Interpretation Notes</h2>
        <ul class="note-list">
            {% for note in payload.interpretation_notes %}
            <li>{{ note }}</li>
            {% endfor %}
        </ul>

        <h2>Appendix: Prompt / Model / Score Rows</h2>
        <div class="table-wrap">
            <table id="appendix">
                <thead>
                    <tr>
                        <th onclick="sortTable('appendix',0)">Case ID</th>
                        <th onclick="sortTable('appendix',1)">Dimension</th>
                        <th onclick="sortTable('appendix',2)">Model</th>
                        <th onclick="sortTable('appendix',3)">Status</th>
                        <th onclick="sortTable('appendix',4)">Score</th>
                        <th onclick="sortTable('appendix',5)">Latency (ms)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in payload.appendix_rows %}
                    <tr>
                        <td>{{ row.case_id }}</td>
                        <td>{{ row.dimension }}</td>
                        <td>{{ row.model_id }}</td>
                        <td>{{ row.status }}</td>
                        <td>{{ row.score }}</td>
                        <td>{{ row.latency_ms }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </main>

    <script>
        function sortTable(tableId, columnIndex) {
            const table = document.getElementById(tableId);
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            const isNumeric = rows.every(r => !isNaN(parseFloat(r.cells[columnIndex].innerText)));
            const currentDir = table.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
            rows.sort((a, b) => {
                const av = a.cells[columnIndex].innerText.trim();
                const bv = b.cells[columnIndex].innerText.trim();
                if (isNumeric) {
                    const an = parseFloat(av || '0');
                    const bn = parseFloat(bv || '0');
                    return currentDir === 'asc' ? an - bn : bn - an;
                }
                return currentDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
            });
            rows.forEach(r => tbody.appendChild(r));
            table.setAttribute('data-sort-dir', currentDir);
        }
    </script>
</body>
</html>
"""
