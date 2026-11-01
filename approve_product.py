#!/usr/bin/env python3
"""Mechanical approval gate for Gumroad products.

This runs the OBJECTIVE checks so a human never has to. A separate reviewer agent
handles the subjective quality call; this script only ever blocks on facts.

Usage:
    approve_product.py <product_id> [--json]

Exit code 0 = APPROVED, 1 = REJECTED, 2 = could not check.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

GUMROAD = os.environ.get("GUMROAD_BIN") or shutil.which("gumroad") or "gumroad"

# Phrases that promise things a digital download cannot deliver. The skill's
# hard rule: never promise video, walkthroughs or refund guarantees.
FORBIDDEN = [
    (r"\bvideo\s+(lesson|lessons|course|tutorial|walkthrough|series|training)s?\b",
     "promises video content"),
    (r"\bmp4\b|\bscreencast\b|\bscreen\s*recording\b", "promises video files"),
    (r"\b1[- ]on[- ]1\b|\bcoaching call\b|\blive session\b", "promises live/1:1 time"),
    (r"\bmoney[- ]back guarantee\b|\bguaranteed refund\b", "promises a refund guarantee"),
    (r"\blifetime (updates|support)\b", "promises lifetime updates"),
    (r"\b(discord|community) access\b", "promises community access"),
]

MINB = 400  # bytes; anything smaller is a stub, not a deliverable

# Some files are legitimately tiny: config manifests, ignore files, lockfiles.
# Flagging those as "stubs" is a false positive, so they are exempt from the
# size test (they must still download successfully).
SMALL_OK = re.compile(
    r"(^|/)(requirements\.txt|\.gitignore|\.gitattributes|package\.json|"
    r"pyproject\.toml|config\.example\.[a-z]+|\.env\.example|LICENSE|"
    r"[^/]+\.(cfg|ini|lock|editorconfig))$", re.I)


def sh(args, timeout=90):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def check(pid):
    out = {"product_id": pid, "checks": [], "approved": True}

    def fail(msg):
        out["checks"].append(("FAIL", msg))
        out["approved"] = False

    def ok(msg):
        out["checks"].append(("ok", msg))

    r = sh([GUMROAD, "products", "view", pid, "--json"])
    if r.returncode != 0 or not r.stdout.strip():
        out["approved"] = False
        out["checks"].append(("FAIL", "could not fetch product from Gumroad"))
        return out, 2
    try:
        p = json.loads(r.stdout)["product"]
    except Exception as e:
        out["approved"] = False
        out["checks"].append(("FAIL", f"unparseable API response: {e}"))
        return out, 2

    out["name"] = p.get("name")
    out["price"] = p.get("price")
    desc = strip_html(p.get("description"))

    # 1. published / draft state
    if p.get("published"):
        ok("published")
    else:
        fail("product is not published")

    # 2. has a real file attached
    files = p.get("files") or []
    if not files:
        fail("no file attached - buyers would receive an empty product")
    else:
        ok(f"{len(files)} file(s) attached")

    # 3. each file actually downloads and is not a stub
    for f in files:
        url = f.get("url")
        if not url:
            fail(f"file {f.get('name')!r} has no download URL")
            continue
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=90) as resp:
                blob = resp.read()
            if len(blob) < MINB and not SMALL_OK.search(f.get("name") or ""):
                fail(f"file {f.get('name')!r} is only {len(blob)}B - looks like a stub")
            else:
                ok(f"{f.get('name')} downloads ({len(blob)}B)")
        except Exception as e:
            fail(f"file {f.get('name')!r} is not downloadable: {str(e)[:70]}")

    # 4. no forbidden promises in the listing
    promise_hits = 0
    for pat, why in FORBIDDEN:
        m = re.search(pat, desc, re.I)
        if m:
            fail(f"listing {why}: {m.group(0)!r}")
            promise_hits += 1
    if promise_hits == 0:
        ok("no forbidden promises (video / refund guarantee / community)")

    # 5. description is substantive enough to sell
    if len(desc) < 120:
        fail(f"description is only {len(desc)} chars - too thin to sell")
    else:
        ok(f"description {len(desc)} chars")

    # 6. metadata present
    if (p.get("covers") or []):
        ok(f"{len(p['covers'])} cover(s)")
    else:
        fail("no cover image")
    if p.get("custom_permalink"):
        ok(f"permalink: {p['custom_permalink']}")
    else:
        fail("no custom permalink set")
    if p.get("tags"):
        ok(f"tags: {', '.join(p['tags'][:6])}")
    else:
        fail("no tags - hurts discoverability")

    # 7. price sanity
    price = p.get("price")
    if price is None:
        fail("no price set")
    else:
        dollars = price / 100 if price > 200 else price
        if dollars < 0:
            fail("negative price")
        else:
            ok(f"price ${dollars:.2f}")

    return out, (0 if out["approved"] else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product_id")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out, code = check(a.product_id)
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"{'APPROVED' if out['approved'] else 'REJECTED'}  {out.get('name')}  ({a.product_id})")
        for status, msg in out["checks"]:
            print(f"   [{'x' if status == 'FAIL' else ' '}] {msg}")
    sys.exit(code)


if __name__ == "__main__":
    main()
