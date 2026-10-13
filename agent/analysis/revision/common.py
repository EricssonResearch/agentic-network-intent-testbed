#!/usr/bin/env python3
"""
Shared helpers for the revision analysis modules (regret, reasoning, latency_invalid,
threshold_metrics, monotonicity, make_figures, tables_to_tex).

Contents
  * canonical backend order / labels / scenario labels used in every table and figure
  * argparse helpers (--campaign, --out-dir, --min-decisions) and `load_campaign`
  * `Table` (columns + rows -> markdown / booktabs LaTeX) and `Numbers` (every reported
    number with its definition -> numbers.json / macros.tex)
  * small statistics not in stats_report.py: Wilson CI, t-based mean CI, Spearman
    (scipy if available, manual fallback), Cohen's kappa, quantiles
  * action parsing (type, syntax validity) shared by several modules

Nothing here duplicates stats_report.py (Welch, Hedges g, Holm, TOST, bootstrap, power);
import those from stats_report directly.
"""
from __future__ import annotations
import argparse, json, math, re, statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

from load_runs import Episode, MIN_DECISIONS, load_all

REPO = Path(__file__).resolve().parents[3]


def open_gamelog(path):
    """Text handle for an engine log stored as gamelog.txt or gamelog.txt.gz (the released data ships the logs
    gzip-compressed); None if neither exists."""
    import gzip
    p = Path(path)
    if p.suffix == ".gz" and p.exists():
        return gzip.open(p, "rt", errors="ignore")
    if p.exists():
        return open(p, errors="ignore")
    gz = p.with_name(p.name + ".gz")
    return gzip.open(gz, "rt", errors="ignore") if gz.exists() else None


def gamelog_text(path) -> str:
    h = open_gamelog(path)
    if h is None:
        return ""
    with h:
        return h.read()
REVISION_DIR = REPO / "paper_major_revision"
DEFAULT_TABLES_DIR = REVISION_DIR / "tables"
DEFAULT_FIGURES_DIR = REVISION_DIR / "figures"

BACKEND_ORDER = ["llm", "llm_nospatial", "llm_minimal", "rule", "greedy", "random", "noop", "replay"]
BACKEND_LABEL = {"llm": "LLM-full", "llm_nospatial": "LLM-nospatial", "llm_minimal": "LLM-minimal",
                 "rule": "rule", "greedy": "greedy-candidate", "random": "random", "noop": "noop", "replay": "replay", "llm_v3test": "LLM-v3test"}
SCENARIO_ORDER = ["s1_peaceful", "s2_stress", "s3_daynight", "s4_adversarial"]
SCENARIO_LABEL = {"s1_peaceful": "S1 Peaceful", "s2_stress": "S2 Stress", "s3_daynight": "S3 Day/Night",
                  "s4_adversarial": "S4 Adversarial"}
DECISION_INTERVAL_S = 60.0   # simulated seconds between decision epochs (both protocols)

ACTION_RE = {
    "noop": re.compile(r"^noop$"),
    "place_bs": re.compile(r"^place_bs\|(macro_cell|small_cell|micro_cell)\|-?\d+\|-?\d+$"),
    "reconfig_slice": re.compile(r"^reconfig_slice\|\d+\|\d*\.?\d+\|\d*\.?\d+\|\d*\.?\d+$"),
}


# ----------------------------------------------------------------------------- labels
def backend_label(b: str) -> str:
    return BACKEND_LABEL.get(b, b.replace("_", "-"))


def scenario_label(s: str) -> str:
    return SCENARIO_LABEL.get(s, s.replace("_", " "))


def backend_sort_key(b: str) -> tuple:
    return (BACKEND_ORDER.index(b) if b in BACKEND_ORDER else len(BACKEND_ORDER), b)


def scenario_sort_key(s: str) -> tuple:
    return (SCENARIO_ORDER.index(s) if s in SCENARIO_ORDER else len(SCENARIO_ORDER), s)


def group_sort_key(key: tuple) -> tuple:
    """Sort key for (scenario, backend[, ...]) tuples."""
    sc, be = key[0], key[1]
    return scenario_sort_key(sc) + backend_sort_key(be) + tuple(str(k) for k in key[2:])


# ----------------------------------------------------------------------------- CLI / loading
def add_common_args(ap: argparse.ArgumentParser, default_out: Optional[Path] = None) -> argparse.ArgumentParser:
    ap.add_argument("--campaign", choices=["v1", "v2", "all"], default="v2", help="which campaign(s) to analyse")
    ap.add_argument("--out-dir", default=str(default_out) if default_out else None, help="where to write outputs (created)")
    ap.add_argument("--min-decisions", type=int, default=None,
                    help=f"validity threshold on decisions per episode (default {MIN_DECISIONS}; env ANALYSIS_MIN_DECISIONS); "
                         "lower it to include short pilot episodes in smoke tests")
    ap.add_argument("--keep-replay", action="store_true", help="keep 'replay' backend episodes (excluded by default)")
    return ap


def load_campaign(args) -> list[Episode]:
    eps = load_all(args.campaign in ("v1", "all"), args.campaign in ("v2", "all"), only_valid=True,
                   min_decisions=args.min_decisions)
    if not getattr(args, "keep_replay", False):
        eps = [e for e in eps if e.backend != "replay"]
    return eps


def campaign_note(args, eps: Sequence[Episode]) -> str:
    thr = args.min_decisions if args.min_decisions is not None else MIN_DECISIONS
    return (f"campaign={args.campaign}; valid episodes={len(eps)}; min decisions per episode={thr}; "
            f"protocols={sorted({e.protocol for e in eps})}")


# ----------------------------------------------------------------------------- formatting
def tex_escape(s: str) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
            .replace("#", r"\#").replace("$", r"\$"))


_UNICODE_TEX = {"±": r"$\pm$", "≥": r"$\geq$", "≤": r"$\leq$", "·": r"$\cdot$", "Δ": r"$\Delta$", "κ": r"$\kappa$", "ρ": r"$\rho$",
                "→": r"$\rightarrow$", "−": "$-$"}


def tex_cell(s) -> str:
    """Escape a table cell for LaTeX. Cells that already contain a backslash are taken as pre-escaped LaTeX
    (e.g. '\\%', '$\\pm$') and passed through; plain cells get %, _, &, # escaped and ± ≥ ≤ · turned into math."""
    s = str(s)
    if "\\" in s:
        return s
    s = s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
    for u, t in _UNICODE_TEX.items():
        s = s.replace(u, t)
    return s


def fmt(x, nd: int = 1) -> str:
    """Number -> string; None/NaN -> 'n/a'."""
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return "n/a"
    if isinstance(x, int) or (isinstance(x, float) and nd == 0):
        return f"{int(round(x))}"
    return f"{x:.{nd}f}"


def fmt_pm(mean, sd, nd: int = 1) -> str:
    return "n/a" if mean is None else f"{fmt(mean, nd)} ± {fmt(sd, nd)}"


def fmt_ci(ci, nd: int = 1) -> str:
    return "n/a" if ci is None else f"[{fmt(ci[0], nd)}, {fmt(ci[1], nd)}]"


def fmt_p(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


# ----------------------------------------------------------------------------- tables
@dataclass
class Table:
    """A table that renders to markdown and to a booktabs LaTeX fragment.

    rows contain already-formatted strings (use fmt*). `colspec` defaults to l + r*(n-1).
    `wide=True` emits tabular* over \\tblwidth (the els-cas class macro used in the paper)."""
    name: str
    caption: str
    columns: list
    rows: list = field(default_factory=list)
    label: Optional[str] = None
    colspec: Optional[str] = None
    note: str = ""
    wide: bool = False

    def to_markdown(self) -> str:
        out = ["| " + " | ".join(self.columns) + " |", "|" + "---|" * len(self.columns)]
        for r in self.rows:
            out.append("| " + " | ".join(str(c) for c in r) + " |")
        if self.note:
            out += ["", f"*{self.note}*"]
        return "\n".join(out)

    def to_tex(self) -> str:
        spec = self.colspec or ("l" + "r" * (len(self.columns) - 1))
        label = self.label or f"tab:{self.name}"
        wide = self.wide or len(self.columns) > 7
        L = [f"% auto-generated by {self.name}: do not edit by hand (tables_to_tex.py / revision modules)",
             r"\begin{table}[t]", r"\centering" + (r"\footnotesize\setlength{\tabcolsep}{4pt}" if wide else r"\small"),
             f"\\caption{{{self.caption}}}\\label{{{label}}}"]
        if wide:
            # natural-width tabular, scaled down to the text width only when it is too wide (adjustbox max width)
            L += [r"\begin{adjustbox}{max width=\textwidth}", f"\\begin{{tabular}}{{{spec}}}", r"\toprule",
                  " & ".join(tex_cell(c) for c in self.columns) + r" \\", r"\midrule"]
        else:
            L += [f"\\begin{{tabular}}{{{spec}}}", r"\toprule",
                  " & ".join(tex_cell(c) for c in self.columns) + r" \\", r"\midrule"]
        for r in self.rows:
            L.append(" & ".join(tex_cell(c) for c in r) + r" \\")
        L += [r"\bottomrule", r"\end{tabular}"]
        if wide:
            L.append(r"\end{adjustbox}")
        if self.note:
            L.append(r"\par\smallskip\footnotesize " + tex_cell(self.note))
        L.append(r"\end{table}")
        return "\n".join(L) + "\n"


def write_table(t: Table, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{t.name}.tex"
    p.write_text(t.to_tex())
    return p


# ----------------------------------------------------------------------------- numbers registry
def macro_name(key: str) -> str:
    """'s1_peaceful_llm_avg_cov' -> 'numSOnePeacefulLlmAvgCov' (LaTeX macro names: letters only)."""
    digits = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
              "8": "Eight", "9": "Nine"}
    parts = re.split(r"[^A-Za-z0-9]+", key)
    out = "num"
    for p in parts:
        if not p:
            continue
        chunk = "".join(digits[c] if c.isdigit() else c for c in p)
        out += chunk[0].upper() + chunk[1:]
    return out


class Numbers:
    """Registry of every number that appears in the paper, with its definition."""

    def __init__(self):
        self.items: dict = {}

    def add(self, key: str, value, definition: str, n=None, unit: str = "", nd: int = 1, source: str = ""):
        self.items[key] = dict(value=value, definition=definition, n=n, unit=unit, nd=nd, source=source,
                               text=fmt(value, nd) if not isinstance(value, str) else value)
        return value

    def update(self, other: "Numbers"):
        self.items.update(other.items)

    def to_json(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.items, indent=2, default=str) + "\n")

    def to_macros(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        L = ["% auto-generated by tables_to_tex.py: \\input{tables/macros.tex} and use \\numXxx in the text",
             "% every macro corresponds to a key in numbers.json (definition there)"]
        seen = set()
        for k, v in sorted(self.items.items()):
            m = macro_name(k)
            if m in seen:
                m += "X"
            seen.add(m)
            L.append(f"\\newcommand{{\\{m}}}{{{tex_escape(v['text'])}}}  % {k}: {v['definition'][:90]}")
        path.write_text("\n".join(L) + "\n")


# ----------------------------------------------------------------------------- statistics
def quantile(xs: Sequence[float], p: float) -> Optional[float]:
    """Linear-interpolated quantile (numpy default), p in [0,1]."""
    xs = sorted(xs)
    if not xs:
        return None
    if len(xs) == 1:
        return float(xs[0])
    h = (len(xs) - 1) * p
    lo, hi = math.floor(h), math.ceil(h)
    return float(xs[lo] + (xs[hi] - xs[lo]) * (h - lo))


def mean_sd(xs: Sequence[float]) -> tuple:
    xs = list(xs)
    if not xs:
        return None, None
    return statistics.fmean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def mean_ci_t(xs: Sequence[float], conf: float = 0.95) -> Optional[tuple]:
    """t-based CI of the mean; None if n < 2."""
    xs = list(xs)
    if len(xs) < 2:
        return None
    try:
        from scipy import stats as st
        tc = st.t.ppf(0.5 + conf / 2, len(xs) - 1)
    except Exception:
        tc = 1.96
    m, sd = mean_sd(xs)
    h = tc * sd / math.sqrt(len(xs))
    return (m - h, m + h)


def wilson_ci(k: int, n: int, z: float = 1.959964) -> Optional[tuple]:
    """Wilson score interval for a binomial proportion (returned as fractions)."""
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def _ranks(xs: Sequence[float]) -> list:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> tuple:
    """Spearman rho and two-sided p (scipy if present, else manual rho with t-approximation p)."""
    if len(x) < 3 or len(x) != len(y):
        return None, None
    try:
        from scipy import stats as st
        r = st.spearmanr(x, y)
        return float(r.correlation), float(r.pvalue)
    except Exception:
        rx, ry = _ranks(x), _ranks(y)
        mx, my = statistics.fmean(rx), statistics.fmean(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
        if den == 0:
            return None, None
        rho = num / den
        n = len(x)
        t = rho * math.sqrt((n - 2) / max(1e-12, 1 - rho * rho))
        p = 2 * (1 - _t_cdf(abs(t), n - 2))
        return rho, p


def _t_cdf(t: float, df: int) -> float:
    """Student t CDF via the regularised incomplete beta (no scipy)."""
    x = df / (df + t * t)
    ib = _betainc(df / 2, 0.5, x)
    return 1 - 0.5 * ib if t >= 0 else 0.5 * ib


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b + lbeta) / a
    # Lentz continued fraction
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 400):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1 + num * d
        d = 1 / (d if abs(d) > 1e-30 else 1e-30)
        c = 1 + num / (c if abs(c) > 1e-30 else 1e-30)
        f *= c * d
        if abs(c * d - 1) < 1e-12:
            break
    return front * (f - 1)


def cohen_kappa(a: Sequence, b: Sequence) -> Optional[float]:
    """Cohen's kappa for two label sequences over the same items (any hashable labels)."""
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    labels = sorted(set(a) | set(b), key=str)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((sum(1 for x in a if x == l) / n) * (sum(1 for y in b if y == l) / n) for l in labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


# ----------------------------------------------------------------------------- actions
def action_type(action: str) -> str:
    """'noop' | 'place_bs' | 'reconfig_slice' | 'other' (by prefix, as in Episode.action_counts)."""
    head = (action or "").split("|")[0].strip()
    return head if head in ("noop", "place_bs", "reconfig_slice") else "other"


def action_syntax_valid(action: str) -> bool:
    """True if the action string matches the bridge grammar (e.g. rejects 'place_bs|macro_cell|X|Z')."""
    a = (action or "").strip()
    return any(rx.match(a) for rx in ACTION_RE.values())


def state(d: dict, key: str, default=None):
    return d.get("state_summary", {}).get(key, default)


def units_for_coverage(d: dict) -> Optional[int]:
    """Denominator of coverage_pct: mobile_units (v2 state) else total_units (v1; approximation, see bridge)."""
    ss = d.get("state_summary", {})
    return ss.get("mobile_units", ss.get("total_units"))


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n")
    return path


# ----------------------------------------------------------------------------- module result
@dataclass
class Result:
    """What every analysis module's analyze() returns; consumed by tables_to_tex.py and make_figures.py."""
    tables: list = field(default_factory=list)          # list[Table]
    numbers: Numbers = field(default_factory=Numbers)
    markdown: str = ""
    extra: dict = field(default_factory=dict)            # per-event rows, series, etc.

    def write(self, out_dir: Path, stem: str) -> list:
        """Write <stem>.md and every table as <table.name>.tex into out_dir; returns the paths."""
        out_dir = Path(out_dir)
        paths = [write_text(out_dir / f"{stem}.md", self.markdown)]
        for t in self.tables:
            paths.append(write_table(t, out_dir))
        return paths
