#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(
    os.getenv("RETENTION_EVIDENCE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "evidence")
)


def text(value: object) -> str:
    return html.escape(str(value))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=EVIDENCE_DIR / "m6-model-evaluation.json")
    parser.add_argument("--output", type=Path, default=EVIDENCE_DIR / "m6-model-stakeholder.svg")
    arguments = parser.parse_args()
    report = json.loads(arguments.report.read_text())
    baseline = report["models"]["logistic_regression"]
    challenger = report["models"]["histogram_gradient_boosting"]
    repeat = report["repeat_subscriber_evaluation"]
    new = report["subgroups"]["is_repeat_subscriber"]["march_new"]
    contract = report["evaluation_contract"]
    top_mix = report["top_decile_composition"]

    improvement = report["relative_log_loss_improvement"] * 100
    interval = report["intervals_95"]["relative_log_loss_improvement"]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
<rect width="1600" height="1000" fill="#e8ece9"/>
<rect width="1600" height="116" fill="#102a3d"/>
<text x="64" y="54" font-family="Avenir Next,Segoe UI,sans-serif" font-size="31" font-weight="700" fill="#f7f6f0">Subscriber Retention Intelligence</text>
<text x="64" y="86" font-family="Avenir Next,Segoe UI,sans-serif" font-size="16" fill="#bbccd5">M6 model-selection docket · held-out March 2017</text>
<text x="1536" y="60" text-anchor="end" font-family="Avenir Next,Segoe UI,sans-serif" font-size="15" fill="#d7e1e5">ONE THREAD · NO DOCKER · {report["runtime_seconds"]:.1f}s</text>

<text x="64" y="166" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" letter-spacing="2" fill="#813720">DECISION</text>
<text x="64" y="230" font-family="Avenir Next,Segoe UI,sans-serif" font-size="49" font-weight="750" fill="#102a3d">Ship challenger for repeat subscribers.</text>
<text x="64" y="275" font-family="Avenir Next,Segoe UI,sans-serif" font-size="24" fill="#4d6473">March-new probabilities fail calibration. Exclude them from action until a representative future window exists.</text>

<rect x="64" y="320" width="460" height="206" fill="#f7f6f0" stroke="#bdc8c4"/>
<text x="92" y="362" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" fill="#813720">LOG LOSS</text>
<text x="92" y="422" font-family="Avenir Next,Segoe UI,sans-serif" font-size="46" font-weight="750" fill="#102a3d">{challenger["log_loss"]:.3f}</text>
<text x="92" y="454" font-family="Avenir Next,Segoe UI,sans-serif" font-size="16" fill="#4d6473">challenger vs {baseline["log_loss"]:.3f} logistic</text>
<text x="92" y="494" font-family="Avenir Next,Segoe UI,sans-serif" font-size="19" font-weight="700" fill="#1f6959">{improvement:.1f}% lower · CI {interval[0] * 100:.1f}%–{interval[1] * 100:.1f}%</text>

<rect x="540" y="320" width="460" height="206" fill="#f7f6f0" stroke="#bdc8c4"/>
<text x="568" y="362" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" fill="#813720">CALIBRATION ERROR</text>
<text x="568" y="422" font-family="Avenir Next,Segoe UI,sans-serif" font-size="46" font-weight="750" fill="#102a3d">{challenger["expected_calibration_error"]:.3f}</text>
<text x="568" y="454" font-family="Avenir Next,Segoe UI,sans-serif" font-size="16" fill="#4d6473">full held-out population · gate ≤ 0.030</text>
<text x="568" y="494" font-family="Avenir Next,Segoe UI,sans-serif" font-size="19" font-weight="700" fill="#1f6959">Repeat scope: {repeat["challenger"]["expected_calibration_error"]:.3f}</text>

<rect x="1016" y="320" width="520" height="206" fill="#a4482f"/>
<text x="1044" y="362" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" fill="#ffe0d3">TOP-DECILE LIFT</text>
<text x="1044" y="422" font-family="Avenir Next,Segoe UI,sans-serif" font-size="46" font-weight="750" fill="#fff8f3">{challenger["top_decile_lift"]:.2f}×</text>
<text x="1044" y="454" font-family="Avenir Next,Segoe UI,sans-serif" font-size="16" fill="#ffe0d3">observed churn vs held-out population</text>
<text x="1044" y="494" font-family="Avenir Next,Segoe UI,sans-serif" font-size="19" font-weight="700" fill="#fff8f3">Repeat scope: {repeat["challenger"]["top_decile_lift"]:.2f}×</text>

<text x="64" y="584" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" letter-spacing="2" fill="#813720">TIME AND POPULATION CONTRACT</text>
<line x1="64" y1="608" x2="1536" y2="608" stroke="#879a96"/>
<circle cx="144" cy="670" r="12" fill="#102a3d"/><line x1="156" y1="670" x2="460" y2="670" stroke="#879a96" stroke-width="3"/>
<circle cx="484" cy="670" r="12" fill="#102a3d"/><line x1="496" y1="670" x2="800" y2="670" stroke="#879a96" stroke-width="3"/>
<circle cx="824" cy="670" r="12" fill="#a4482f"/>
<text x="104" y="712" font-family="Avenir Next,Segoe UI,sans-serif" font-size="18" font-weight="700" fill="#102a3d">Fit · Feb</text>
<text x="104" y="740" font-family="Avenir Next,Segoe UI,sans-serif" font-size="15" fill="#4d6473">{contract["fit"]["rows"]:,} fixed hash rows</text>
<text x="444" y="712" font-family="Avenir Next,Segoe UI,sans-serif" font-size="18" font-weight="700" fill="#102a3d">Calibrate · Feb</text>
<text x="444" y="740" font-family="Avenir Next,Segoe UI,sans-serif" font-size="15" fill="#4d6473">{contract["calibration"]["rows"]:,} disjoint rows</text>
<text x="784" y="712" font-family="Avenir Next,Segoe UI,sans-serif" font-size="18" font-weight="700" fill="#102a3d">Test · Mar</text>
<text x="784" y="740" font-family="Avenir Next,Segoe UI,sans-serif" font-size="15" fill="#4d6473">{contract["test"]["rows"]:,} untouched rows</text>

<rect x="1030" y="620" width="506" height="160" fill="#f7f6f0" stroke="#bdc8c4"/>
<text x="1058" y="660" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" fill="#813720">POPULATION SHIFT</text>
<text x="1058" y="700" font-family="Avenir Next,Segoe UI,sans-serif" font-size="28" font-weight="750" fill="#102a3d">March-new churn {new["churn_rate"] * 100:.1f}%</text>
<text x="1058" y="732" font-family="Avenir Next,Segoe UI,sans-serif" font-size="16" fill="#4d6473">ECE {new["challenger_ece"]:.3f} · {top_mix["march_new_share"] * 100:.1f}% of global top decile</text>
<text x="1058" y="760" font-family="Avenir Next,Segoe UI,sans-serif" font-size="15" font-weight="700" fill="#973a2c">Probability use blocked for this group.</text>

<rect x="64" y="822" width="1472" height="118" fill="#102a3d"/>
<text x="92" y="860" font-family="Avenir Next,Segoe UI,sans-serif" font-size="14" font-weight="800" letter-spacing="2" fill="#d46b4d">GUARDRAILS</text>
<text x="92" y="895" font-family="Avenir Next,Segoe UI,sans-serif" font-size="17" fill="#f7f6f0">Age, gender, city, identifiers, outcomes, and post-cutoff activity excluded from scoring.</text>
<text x="92" y="922" font-family="Avenir Next,Segoe UI,sans-serif" font-size="17" fill="#bbccd5">Only two observed windows exist. Calibration is disjoint, not a third time period. Association is not intervention effect.</text>
</svg>"""
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(svg)
    print(text(arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
