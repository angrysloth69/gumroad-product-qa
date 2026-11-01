# gumroad-product-qa

**Catch digital products that look fine but deliver nothing.**

A product can be live, priced, tagged, cover-imaged and perfectly presented — and still be broken. The attached file is a 200-byte stub. The listing promises a video course that was never recorded. There's no permalink, so nothing can find it.

Buyers discover that, not you. You find out through refunds, one-star reviews and Gumroad disputes.

This is a small QA gate you can run before you publish, or in CI on every product change. It checks the objective facts an API can verify, so you never have to eyeball 15 listings again.

## What it checks

- Product is **published**
- At least one **file is attached**
- Every attached file **actually downloads**, and isn't a stub
  (config manifests like `requirements.txt` and `.gitignore` are exempt, so tiny-but-legitimate files don't produce false alarms)
- The listing makes **no promise a download can't keep** — video lessons, walkthroughs, 1:1 calls, money-back guarantees, lifetime updates, community access
- Description is **substantive enough to sell** (not a one-liner)
- **Cover image** present
- **Custom permalink** set (without one, nothing can link to your product cleanly)
- **Tags** present (affects discoverability)
- **Price** is sane

Subjective quality — is the content actually *good* — is not something a script can judge. This tool is deliberately the mechanical half: it only ever blocks on facts.

## Usage

```bash
# once
npm i -g @gumroad/cli    # or: curl -fsSL https://gumroad.com/install-cli.sh | bash
gumroad auth login

# check one product
python3 approve_product.py <product_id>

# machine-readable
python3 approve_product.py <product_id> --json
```

Exit codes: `0` approved · `1` rejected · `2` could not check.

```
APPROVED  Excel Pricing Calculator for Service Businesses  (abc123==)
   [ ] published
   [ ] 7 file(s) attached
   [ ] pricing-engine.xlsx downloads (48213B)
   [ ] no forbidden promises (video / refund guarantee / community)
   [ ] description 812 chars
   [ ] 2 cover(s)
   [ ] permalink: excel-pricing-calculator
   [ ] tags: excel, pricing, freelance, calculator
   [ ] price $46.00
```

## Use it in CI

Reject the build if any product regresses:

```yaml
- run: |
    for id in $(cat product-ids.txt); do
      python3 approve_product.py "$id" --json | jq -e '.approved' > /dev/null \
        || { echo "product $id failed QA"; exit 1; }
    done
```

## Get your product ids

```bash
gumroad products list --all --json | jq -r '.products[] | "\(.id)\t\(.name)"'
```

Note the `--all`. Plain `products list` returns only the first page, which silently under-reports your catalogue.

## Requirements

- Python 3.8+ (standard library only — no dependencies)
- The official [gumroad CLI](https://github.com/antiwork/gumroad-cli), authenticated
- Set `GUMROAD_BIN` if the binary isn't on your `PATH`

## Why this exists

Written after auditing a catalogue of digital products and finding the gap between what the listings promised and what the files actually contained. Checking that by hand doesn't scale, and it's exactly the kind of thing you skip when you're shipping fast.

## License

MIT — see [LICENSE](LICENSE).

---

If you sell digital products and want to skip the "build the whole thing" part, I keep a small store of spreadsheets, Notion templates and dev tooling at **https://gavinjohnson3.gumroad.com** — plus a set of free ones if you just want to see how they're put together.
