"""Scoring of the national catalogue validation samples.

Pure functions over a candidates file and one or more runs files; no simulation.
Standard library and numpy only; every random step uses a fixed seed.

Match rule (as the merged-code scoring): a building matches when any of its
renovation states lies within +-20 % of the measured heating. Simulated heating
is the sum of ``period_piece_heating_kwh`` over the measured calendar years; for
multifamily buildings the airing term (4.0 kWh/m2 x Fgeo) and the hot-water
circulation term (25 x (1/0.75 - 1) kWh/m2) are added, both per m2 Atemp, scaled
to the measured period and converted to carrier input (heat pump / 2.75, fuel
/ 0.9). The last row per building, state and year counts. A building with any
missing or non-accepted run is excluded from scoring and counted with its reason.

    python robust_score.py score --sample hold-out=CANDIDATES:RUNS[,RUNS...] \
        --sample calibration=... --out DIR/name
    python robust_score.py compare --spec spec.json --out DIR/name

A later runs file overrides earlier rows for the same building, state and year,
so a variant can be scored as ``base_runs,variant_runs``.

Acceptance rule for a future change (see ``compare_samples``): a change is
accepted only if it gains matches (gained > lost) in BOTH samples and the exact
McNemar p of the pooled gained/lost counts is below 0.05.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FGEO_PATH = HERE / "fgeo.json"
BENCHMARK_PATH = HERE / "results_benchmark/benchmark.json"

TOLERANCE = 0.2
STATES = ("existing", "standard", "advanced")
CATEGORIES = ("single_family", "multi_family", "office", "school")
AIRING_KWH_M2 = 4.0  # x Fgeo, per m2 Atemp and year
CIRCULATION_KWH_M2 = 25 * (1 / 0.75 - 1)  # per m2 Atemp and year
HEAT_PUMP_COP = 2.75
FUEL_EFFICIENCY = 0.9
N_PERMUTATIONS = 2000
N_BOOTSTRAP = 2000
PERMUTATION_SEED = 20261121
BOOTSTRAP_SEED = 20261122
GEOMETRY_HIGH = 1.1  # Atemp / model conditioned area above this: model smaller than Atemp
GEOMETRY_LOW = 0.6
ORACLE_GRID = np.exp(np.linspace(math.log(0.25), math.log(4.0), 2773))  # step ~0.1 %


# ---------------------------------------------------------------- input

def read_jsonl(path):
    with open(path) as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_candidates(path):
    """Kept buildings: the last row per (category, era, building) with ``kept`` true."""
    latest = {}
    for r in read_jsonl(path):
        latest[(r["category"], r["era"], r["building_id"])] = r
    return {r["building_id"]: r for r in latest.values() if r.get("kept") is True}


def last_rows(paths):
    """{(building, state, year): row}; later rows and later files win."""
    rows = {}
    for path in ([paths] if isinstance(paths, (str, Path)) else paths):
        for r in read_jsonl(path):
            rows[(r["building_id"], r["state"], r["year"])] = r
    return rows


def load_fgeo(path=FGEO_PATH):
    return json.loads(Path(path).read_text())["fgeo"]


def load_stock(path=BENCHMARK_PATH):
    """Measured-target stock count per cohort label ``"category era"``."""
    return {k: v["measured"] for k, v in json.loads(Path(path).read_text())["counts"].items()}


# ---------------------------------------------------------------- per building

def states_for(era):
    return (None,) if era == "SE.07" else STATES


def cohort(c):
    return f"{c['category']} {c['era']}"


def period_days(c):
    return (date.fromisoformat(c["period_end_exclusive"]) - date.fromisoformat(c["period_start"])).days


def carrier_term(c, kwh_m2_year):
    """A per-m2-Atemp yearly heat term as carrier input over the measured period."""
    v = kwh_m2_year * c["epc_atemp_m2"] * period_days(c) / 365
    if c["carrier"] == "heat_pump":
        v /= HEAT_PUMP_COP
    elif c["carrier"] == "fuel":
        v /= FUEL_EFFICIENCY
    return v


def multifamily_terms(c, fgeo):
    if c["category"] != "multi_family":
        return 0.0
    return carrier_term(c, AIRING_KWH_M2 * fgeo[c["municipality_code"]]) + carrier_term(c, CIRCULATION_KWH_M2)


def simulated(c, rows, fgeo):
    """({state: simulated kWh over the measured period}, None) or (None, exclusion reason)."""
    bid = c["building_id"]
    out = {}
    for s in states_for(c["era"]):
        tot = 0.0
        for y in c["weather_years"]:
            r = rows.get((bid, s, y))
            if r is None:
                return None, "missing run"
            if r.get("status") != "accepted":
                err = (r.get("error") or "").split(":")
                return None, f"{r.get('status')}: " + ":".join(err[:2]).strip()[:80]
            tot += r["period_piece_heating_kwh"]
        out[s] = tot + multifamily_terms(c, fgeo)
    return out, None


def ratios_of(sim, measured):
    return {s: v / measured for s, v in sim.items()}


def is_match(rs, scale=1.0):
    return any(abs(v * scale - 1) <= TOLERANCE for v in rs.values())


def position(rs):
    if is_match(rs):
        return "match"
    v = list(rs.values())
    if all(x > 1 + TOLERANCE for x in v):
        return "above"
    if all(x < 1 - TOLERANCE for x in v):
        return "below"
    return "between"


def conditioned_area(c, rows):
    for s in states_for(c["era"]):
        for y in c["weather_years"]:
            r = rows.get((c["building_id"], s, y))
            if r and r.get("conditioned_area_m2"):
                return r["conditioned_area_m2"]
    return None


# ---------------------------------------------------------------- statistics

def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"match": k, "n": n, "rate": k / n if n else None, "wilson95": [lo, hi]}


def mcnemar_exact(gained, lost):
    """Two-sided exact McNemar (binomial) p for discordant counts."""
    n = gained + lost
    if n == 0:
        return 1.0
    k = min(gained, lost)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


# ---------------------------------------------------------------- sample scoring

class Sample:
    """Scored buildings of one sample with arrays for the resampling statistics."""

    def __init__(self, name, candidates, rows, fgeo):
        self.name = name
        self.candidates = candidates
        self.excluded = {}
        self.sim = {}
        for bid, c in sorted(candidates.items()):
            sim, why = simulated(c, rows, fgeo)
            if sim is None:
                self.excluded[bid] = why
            else:
                self.sim[bid] = sim
        self.ids = sorted(self.sim)
        self.ratios = {b: ratios_of(self.sim[b], candidates[b]["measured_kwh"]) for b in self.ids}
        self.matches = {b: is_match(self.ratios[b]) for b in self.ids}
        self.area = {b: conditioned_area(candidates[b], rows) for b in self.ids}
        c = [candidates[b] for b in self.ids]
        self.S = np.array([[self.sim[b].get(s, np.nan) for s in STATES] if None not in self.sim[b]
                           else [self.sim[b][None], np.nan, np.nan] for b in self.ids], float).reshape(-1, 3)
        self.measured = np.array([x["measured_kwh"] for x in c], float)
        self.scale = np.array([x["epc_atemp_m2"] * period_days(x) / 365 for x in c], float)
        self.intensity = self.measured / self.scale
        self.category = [x["category"] for x in c]
        self.era = [x["era"] for x in c]
        self.cohort = [cohort(x) for x in c]

    def group(self, key):
        return {"type": self.category, "era": self.era, "cohort": self.cohort}[key]


def match_matrix(S, measured):
    """Boolean match per row of measured (P x n) against simulated states (n x 3)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        r = S[None, :, :] / measured[:, :, None]
        return np.any(np.abs(r - 1) <= TOLERANCE, axis=2)


def permuted_measured(sample, groups, n, seed):
    """Measured intensities (kWh/m2 Atemp, period-normalised) shuffled within groups,
    restored to each building's own Atemp and period."""
    rng = np.random.default_rng(seed)
    labels = {g: i for i, g in enumerate(sorted(set(groups)))}
    gid = np.array([labels[g] for g in groups], float)
    base = np.argsort(gid, kind="stable")
    keys = rng.random((n, len(groups))) + 2 * gid[None, :]
    order = np.argsort(keys, axis=1)
    out = np.empty((n, len(groups)))
    out[:, base] = sample.intensity[order]
    return out * sample.scale[None, :]


def chance(sample, scope, n=N_PERMUTATIONS, seed=PERMUTATION_SEED):
    groups = {"all": ["all"] * len(sample.ids), "type": sample.category, "cohort": sample.cohort}[scope]
    seed_scope = [seed, {"all": 0, "type": 1, "cohort": 2}[scope]]
    m = permuted_measured(sample, groups, n, seed_scope)
    rates = match_matrix(sample.S, m).mean(axis=1)
    return {"scope": scope, "permutations": n, "seed": seed_scope, "mean": float(rates.mean()),
            "p2_5": float(np.percentile(rates, 2.5)), "p97_5": float(np.percentile(rates, 97.5))}


def stock_weighted(sample, stock, n=N_BOOTSTRAP, seed=BOOTSTRAP_SEED):
    by = defaultdict(list)
    for b, coh in zip(sample.ids, sample.cohort):
        by[coh].append(sample.matches[b])
    cohorts = sorted(by)
    missing = [c for c in cohorts if c not in stock]
    cohorts = [c for c in cohorts if c in stock]
    w = np.array([stock[c] for c in cohorts], float)
    w /= w.sum()
    point = float(sum(wi * np.mean(by[c]) for wi, c in zip(w, cohorts)))
    rng = np.random.default_rng(seed)
    draws = np.zeros(n)
    for wi, c in zip(w, cohorts):
        x = np.array(by[c], float)
        draws += wi * x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    covered = sum(stock[c] for c in cohorts)
    return {"rate": point, "bootstrap95": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))],
            "draws": n, "seed": seed, "cohorts": len(cohorts), "cohorts_without_stock_count": missing,
            "stock_covered": covered, "stock_total": sum(stock.values()),
            "stock_share_covered": covered / sum(stock.values())}


def breakdown(sample, key):
    out = {}
    for g in sorted(set(sample.group(key))):
        ids = [b for b, x in zip(sample.ids, sample.group(key)) if x == g]
        out[g] = rate(sum(sample.matches[b] for b in ids), len(ids))
    return out


def geometry(sample):
    ratio = {b: sample.candidates[b]["epc_atemp_m2"] / sample.area[b] for b in sample.ids if sample.area[b]}
    v = np.array(list(ratio.values()))
    flag = {b: ("high" if r > GEOMETRY_HIGH else "low" if r < GEOMETRY_LOW else "ok") for b, r in ratio.items()}

    def sub(which):
        ids = [b for b, f in flag.items() if f == which]
        return rate(sum(sample.matches[b] for b in ids), len(ids))

    by_type = {}
    for cat in CATEGORIES:
        ids = [b for b in ratio if sample.candidates[b]["category"] == cat]
        if ids:
            x = np.array([ratio[b] for b in ids])
            by_type[cat] = {"n": len(ids), "median": float(np.median(x)),
                            "high": sum(flag[b] == "high" for b in ids), "low": sum(flag[b] == "low" for b in ids)}
    return {"definition": "Atemp (EPC) / model conditioned floor area; reported, not excluded",
            "n": len(v), "missing_area": len(sample.ids) - len(v),
            "quantiles": {q: float(np.percentile(v, q)) for q in (5, 25, 50, 75, 95)} if len(v) else {},
            "flag_high_gt": GEOMETRY_HIGH, "flag_low_lt": GEOMETRY_LOW,
            "match_flag_high": sub("high"), "match_flag_low": sub("low"), "match_unflagged": sub("ok"),
            "by_type": by_type}


def score_sample(sample, stock):
    n, k = len(sample.ids), sum(sample.matches.values())
    ch = {s: chance(sample, s) for s in ("all", "type", "cohort")}
    head = rate(k, n)
    return {
        "name": sample.name,
        "kept": len(sample.candidates),
        "scored": n,
        "excluded": len(sample.excluded),
        "excluded_reasons": dict(Counter(sample.excluded.values())),
        "excluded_buildings": sample.excluded,
        "headline": head,
        "by_type": breakdown(sample, "type"),
        "by_era": breakdown(sample, "era"),
        "by_cohort": breakdown(sample, "cohort"),
        "chance": ch,
        "skill_over_within_type_chance": head["rate"] - ch["type"]["mean"],
        "stock_weighted": stock_weighted(sample, stock),
        "position": dict(Counter(position(sample.ratios[b]) for b in sample.ids)),
        "position_by_type": {cat: dict(Counter(position(sample.ratios[b]) for b in sample.ids
                                               if sample.candidates[b]["category"] == cat)) for cat in CATEGORIES},
        "geometry": geometry(sample),
    }


# ---------------------------------------------------------------- reference oracle

def fit_cohort_scales(sample):
    """Per cohort, the scale on the model's own states that maximises matches
    (ties: the scale closest to 1)."""
    scales = {}
    for coh in sorted(set(sample.cohort)):
        rs = [sample.ratios[b] for b, x in zip(sample.ids, sample.cohort) if x == coh]
        counts = np.array([sum(is_match(r, s) for r in rs) for s in ORACLE_GRID])
        best = np.flatnonzero(counts == counts.max())
        scales[coh] = float(ORACLE_GRID[best[np.argmin(np.abs(np.log(ORACLE_GRID[best])))]])
    return scales


def oracle(fit, evaluate):
    """Reference only (not a ceiling): cohort scales fitted on ``fit``, scored on ``evaluate``.
    Cohorts absent from the fitting sample keep scale 1."""
    scales = fit_cohort_scales(fit)
    k = sum(is_match(evaluate.ratios[b], scales.get(coh, 1.0)) for b, coh in zip(evaluate.ids, evaluate.cohort))
    return {"fit": fit.name, "evaluate": evaluate.name, "scales": scales,
            "unscaled_cohorts": sorted(set(evaluate.cohort) - set(scales)),
            **rate(k, len(evaluate.ids))}


# ---------------------------------------------------------------- comparison

def paired(base, variant):
    """Gained/lost between two {building: matched} maps over their common buildings."""
    common = sorted(set(base) & set(variant))
    g = sum((not base[b]) and variant[b] for b in common)
    lo = sum(base[b] and not variant[b] for b in common)
    return {"n": len(common), "dropped": len(set(base) ^ set(variant)),
            "base": sum(base[b] for b in common), "variant": sum(variant[b] for b in common),
            "gained": g, "lost": lo, "mcnemar_p": mcnemar_exact(g, lo)}


def compare_samples(pairs):
    """Judge a change on two (or more) samples.

    ``pairs`` maps sample name -> (base matches, variant matches), each a
    {building_id: bool}. Rule: a change is accepted only if it gains matches
    (gained > lost) in BOTH samples and the exact McNemar p of the pooled
    gained/lost counts is below 0.05. Anything else is rejected.
    """
    per = {name: paired(b, v) for name, (b, v) in pairs.items()}
    g = sum(x["gained"] for x in per.values())
    lo = sum(x["lost"] for x in per.values())
    p = mcnemar_exact(g, lo)
    gains_everywhere = all(x["gained"] > x["lost"] for x in per.values())
    return {"per_sample": per, "pooled": {"gained": g, "lost": lo, "mcnemar_p": p},
            "gains_in_every_sample": gains_everywhere, "accepted": bool(gains_everywhere and p < 0.05),
            "rule": "accept only if gained > lost in every sample and pooled exact McNemar p < 0.05"}


# ---------------------------------------------------------------- report

def pct(x):
    return "–" if x is None else f"{100 * x:.1f} %"


def ci(lo_hi):
    lo, hi = lo_hi
    return "–" if lo is None else f"{100 * lo:.1f}–{100 * hi:.1f} %"


def rate_row(label, r):
    return f"| {label} | {r['match']}/{r['n']} | {pct(r['rate'])} | {ci(r['wilson95'])} |"


def markdown(reports, oracles):
    md = ["# Catalogue validation scores", "",
          "Generated by `validation/catalogue/robust_score.py`. Match = any state within ±20 % of measured heating.", ""]
    for r in reports:
        md += [f"## {r['name']}", "",
               f"Kept {r['kept']}, scored {r['scored']}, excluded {r['excluded']}"
               + (": " + "; ".join(f"{k} ({v})" for k, v in r["excluded_reasons"].items()) if r["excluded"] else "") + ".", "",
               "| set | match | rate | Wilson 95 % |", "|---|---|---|---|", rate_row("**all**", r["headline"])]
        md += [rate_row(k, v) for k, v in r["by_type"].items()]
        md += [rate_row(k, v) for k, v in r["by_era"].items()]
        ch = r["chance"]
        sw = r["stock_weighted"]
        md += ["", "| chance (measured permuted) | mean | 95 % range |", "|---|---|---|"]
        md += [f"| {s} | {pct(ch[s]['mean'])} | {pct(ch[s]['p2_5'])}–{pct(ch[s]['p97_5'])} |" for s in ("all", "type", "cohort")]
        md += ["", f"Skill (match − within-type chance): **{100 * r['skill_over_within_type_chance']:.1f} points**.", "",
               f"Stock-weighted match: **{pct(sw['rate'])}** (bootstrap 95 % {ci(sw['bootstrap95'])}); "
               f"cohorts covered {sw['cohorts']}, {100 * sw['stock_share_covered']:.2f} % of the measured stock.", "",
               "| position | n |", "|---|---|"]
        md += [f"| {p} | {r['position'].get(p, 0)} |" for p in ("match", "above", "below", "between")]
        g = r["geometry"]
        q = g["quantiles"]
        md += ["", f"Geometry (Atemp / model conditioned area, n={g['n']}): median {q.get(50, float('nan')):.2f}, "
               f"5–95 % {q.get(5, float('nan')):.2f}–{q.get(95, float('nan')):.2f}.", "",
               "| geometry flag | match | rate | Wilson 95 % |", "|---|---|---|---|",
               rate_row(f"> {g['flag_high_gt']} (model smaller)", g["match_flag_high"]),
               rate_row(f"< {g['flag_low_lt']}", g["match_flag_low"]),
               rate_row("unflagged", g["match_unflagged"]), "",
               "| cohort | match | rate | Wilson 95 % |", "|---|---|---|---|"]
        md += [rate_row(k, v) for k, v in r["by_cohort"].items()]
        md.append("")
    if oracles:
        md += ["## Reference oracle (not a ceiling)", "",
               "One free scale per cohort on the model's own states, fitted on one sample and scored on another.", "",
               "| fit → evaluate | match | rate | Wilson 95 % |", "|---|---|---|---|"]
        md += [rate_row(f"{o['fit']} → {o['evaluate']}", o) for o in oracles["directions"]]
        md += [f"| mean {k} | | {pct(v)} | |" for k, v in oracles["pair_means"].items()]
        md.append("")
    return "\n".join(md)


def build_samples(specs, fgeo):
    out = []
    for spec in specs:
        name, rest = spec.split("=", 1)
        cand, runs = rest.split(":", 1)
        out.append(Sample(name, load_candidates(cand), last_rows(runs.split(",")), fgeo))
    return out


def score(samples, stock, oracle_pairs=None):
    reports = [score_sample(s, stock) for s in samples]
    by = {s.name: s for s in samples}
    pairs = oracle_pairs or [(a.name, b.name) for a in samples for b in samples if a is not b]
    directions = [oracle(by[a], by[b]) for a, b in pairs]
    means = {}
    for o in directions:
        rev = next((x for x in directions if (x["fit"], x["evaluate"]) == (o["evaluate"], o["fit"])), None)
        key = " ↔ ".join(sorted((o["fit"], o["evaluate"])))
        if rev and key not in means:
            means[key] = (o["rate"] + rev["rate"]) / 2
    return reports, {"label": "reference only, not a ceiling", "directions": directions, "pair_means": means}


def write(out, payload, md):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    out.with_suffix(".md").write_text(md + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--sample", action="append", required=True, help="name=candidates.jsonl:runs.jsonl[,runs2.jsonl]")
    s.add_argument("--oracle", action="append", help="fit:evaluate sample names; default every ordered pair")
    s.add_argument("--fgeo", default=FGEO_PATH)
    s.add_argument("--benchmark", default=BENCHMARK_PATH)
    s.add_argument("--out", required=True, help="output path without suffix")
    c = sub.add_parser("compare")
    c.add_argument("--spec", required=True,
                   help='JSON {"samples": {name: {"candidates": ..., "base_runs": [...], "variant_runs": [...]}}}')
    c.add_argument("--fgeo", default=FGEO_PATH)
    c.add_argument("--benchmark", default=BENCHMARK_PATH)
    c.add_argument("--out", required=True)
    a = p.parse_args(argv)
    fgeo, stock = load_fgeo(a.fgeo), load_stock(a.benchmark)
    if a.cmd == "score":
        samples = build_samples(a.sample, fgeo)
        pairs = [tuple(x.split(":")) for x in a.oracle] if a.oracle else None
        reports, orc = score(samples, stock, pairs)
        write(a.out, {"samples": reports, "oracle": orc}, markdown(reports, orc))
        print(markdown(reports, orc))
    else:
        spec = json.loads(Path(a.spec).read_text())
        pairs, deltas = {}, {}
        for name, x in spec["samples"].items():
            cand = load_candidates(x["candidates"])
            base = Sample(name, cand, last_rows(x["base_runs"]), fgeo)
            var = Sample(name, cand, last_rows(list(x["base_runs"]) + list(x["variant_runs"])), fgeo)
            pairs[name] = (base.matches, var.matches)
            rb, rv = score_sample(base, stock), score_sample(var, stock)
            deltas[name] = {k: {"base": f(rb), "variant": f(rv), "delta": f(rv) - f(rb)} for k, f in (
                ("match_rate", lambda r: r["headline"]["rate"]),
                ("stock_weighted", lambda r: r["stock_weighted"]["rate"]),
                ("skill_over_within_type_chance", lambda r: r["skill_over_within_type_chance"]))}
        result = compare_samples(pairs)
        result["deltas"] = deltas
        md = ["# Comparison", "", f"Rule: {result['rule']}.", "",
              "| sample | n | base | variant | gained | lost | p | Δ match | Δ stock-weighted | Δ skill |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for name, x in result["per_sample"].items():
            d = deltas[name]
            md.append(f"| {name} | {x['n']} | {x['base']} | {x['variant']} | {x['gained']} | {x['lost']} | "
                      f"{x['mcnemar_p']:.3g} | {100 * d['match_rate']['delta']:+.1f} | "
                      f"{100 * d['stock_weighted']['delta']:+.1f} | {100 * d['skill_over_within_type_chance']['delta']:+.1f} |")
        pl = result["pooled"]
        md += ["", f"Pooled: gained {pl['gained']}, lost {pl['lost']}, p = {pl['mcnemar_p']:.3g}. "
               f"**{'ACCEPTED' if result['accepted'] else 'REJECTED'}**."]
        write(a.out, result, "\n".join(md))
        print("\n".join(md))


if __name__ == "__main__":
    main()
