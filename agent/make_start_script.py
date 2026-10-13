#!/usr/bin/env python3
"""Generate a Spring/Recoil start script from a scenario template, overriding MODOPTIONS keys.

Usage: make_start_script.py TEMPLATE OUTPUT [--set KEY=VALUE ...]
Keys that already exist inside the [MODOPTIONS] block are replaced; new keys are appended to it.
MinSpeed/MaxSpeed are engine-level keys that also live in [MODOPTIONS] (GAME\\ModOptions\\MinSpeed).
"""
import argparse, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template"); ap.add_argument("output")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--game-set", action="append", default=[], metavar="KEY=VALUE", help="top-level [GAME] key, e.g. HostPort=8453")
    a = ap.parse_args()
    text = open(a.template).read()
    m = re.search(r"(\[MODOPTIONS\]\s*\{)(.*?)(\n\s*\})", text, re.S)
    if not m:
        sys.exit("no [MODOPTIONS] block in template")
    body = m.group(2)
    for kv in a.set:
        k, v = kv.split("=", 1)
        pat = re.compile(r"^(\s*)" + re.escape(k) + r"\s*=.*?;\s*$", re.M)
        if pat.search(body):
            body = pat.sub(lambda mm: f"{mm.group(1)}{k}={v};", body)
        else:
            body = body.rstrip("\n") + f"\n\t\t{k}={v};"
    out = text[:m.start(2)] + body + text[m.end(2):]
    for kv in a.game_set:
        k, v = kv.split("=", 1)
        pat = re.compile(r"^(\t)" + re.escape(k) + r"\s*=.*?;\s*$", re.M)
        if pat.search(out):
            out = pat.sub(lambda mm: f"{mm.group(1)}{k}={v};", out, count=1)
        else:
            out = re.sub(r"(\[GAME\]\s*\{\n)", lambda mm: mm.group(1) + f"\t{k}={v};\n", out, count=1)
    open(a.output, "w").write(out)
    print(f"start script written: {a.output}")

if __name__ == "__main__":
    main()
