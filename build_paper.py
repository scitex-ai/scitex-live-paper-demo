"""Render the report, register its claims, and export their Clew evidence."""

import hashlib
import json
from pathlib import Path

import pymupdf
import scitex_clew as clew
from scitex_live_paper.evidence import collect_report, find_provider

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "manuscript.pdf"
MANUSCRIPT = ROOT / "manuscript.txt"
METRICS = ROOT / "results/metrics.json"
FIGURE = ROOT / "results/reading-errors.png"


def write_json(name, data):
    (ROOT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def render(pairs, mean):
    manuscript = [
        "Sensor calibration on synthetic readings",
        "Example study | SciTeX Live Paper",
        "Methods",
        "The input archive contains paired reference lengths and simulated sensor readings.",
        "The analysis subtracts each reference from its reading and averages the absolute errors.",
        "Results",
        f"Paired readings = {pairs}",
        f"Mean absolute error = {mean} mm",
        f"Figure 1. Signed errors for the {pairs} simulated readings.",
        "This demonstration uses synthetic data and makes no claim about a physical instrument.",
    ]
    MANUSCRIPT.write_text("\n".join(manuscript) + "\n", encoding="utf-8")
    with pymupdf.open() as document:
        page = document.new_page()
        for text, y, size in zip(
            manuscript, [65, 89, 130, 155, 173, 218, 246, 266, 320, 695],
            [22, 11, 15, 11, 11, 15, 12, 12, 11, 11], strict=True,
        ):
            page.insert_text((52, y), text, fontsize=size, color=(0.1, 0.17, 0.23))
        image = page.insert_image(pymupdf.Rect(52, 336, 543, 658), filename=FIGURE)
        (figure_box,) = page.get_image_rects(image)
        (count_box,) = page.search_for(manuscript[6])
        (mean_box,) = page.search_for(manuscript[7])
        document.save(PDF, no_new_id=True, deflate=True)
        height = page.rect.height
    return manuscript, {
        claim_id: {"page": 1, "bbox": [box.x0, height - box.y1, box.x1, height - box.y0]}
        for claim_id, box in (("count", count_box), ("mean-error", mean_box), ("figure-errors", figure_box))
    }


def build():
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    count = metrics["count"]
    mean = metrics["mean_absolute_error_mm"]
    manuscript, anchors = render(count, mean)
    declarations = [
        ("count", "value", manuscript[6], 7, METRICS, count, "/count"),
        ("mean-error", "value", manuscript[7], 8, METRICS, mean, "/mean_absolute_error_mm"),
        ("figure-errors", "figure", manuscript[8], 9, FIGURE, None, None),
    ]
    registry = []
    with clew.project_root(ROOT):
        for claim_id, kind, statement, line, source, value, pointer in declarations:
            clew.add_claim(
                file_path=str(MANUSCRIPT), line_number=line, claim_id=claim_id,
                claim_type=kind, claim_value=statement, source_file=str(source),
                value=value, source_keys={".": {"pointer": pointer}} if pointer else None,
                tolerance={"abs_tol": 0, "rel_tol": 0} if pointer else None,
            )
            registry.append({
                "claim_id": claim_id, "claim_type": kind, "claim_value": statement,
                "file_path": MANUSCRIPT.name, "line_number": line,
                "source_file": source.relative_to(ROOT).as_posix(),
            })
        _, provider = find_provider("clew")
        report = dict(collect_report(provider, str(ROOT), claim_ids=list(anchors)))

    claims_by_id = {claim["claim_id"]: claim for claim in report["claims"]}
    unresolved = {cid: claims_by_id[cid]["reason"] for cid in anchors
                  if claims_by_id[cid]["state"] != "supported"}
    if unresolved:
        raise SystemExit(f"Unresolved: {unresolved}")
    for claim in registry:
        claim["status"] = "verified"
    report["project_root"] = "."
    write_json("evidence-report.json", report)
    write_json("claims.json", {"schema": "scitex-clew.claims/v1", "claims": registry})
    write_json("pdf-anchors.json", {
        "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "anchors": anchors,
    })


if __name__ == "__main__":
    build()
