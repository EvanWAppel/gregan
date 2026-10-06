# BLOCKED — what I need from Evan

Nothing blocked right now.

- [ ] 🔴 **Dedicated, spend-capped Anthropic key for gregan's Ask Tiresias page** — in the Anthropic Console create a separate workspace (e.g. `tiresias-gregan`), set a monthly spend limit + alert (Elvis uses $10), mint a key there, and put it in `gregan/.env` as `ANTHROPIC_API_KEY=…` (for the local live eval) and in Railway → gregan → Variables (for the page). Then tell Claude it is not your personal/default key. Until then the page shows a "needs a key" notice and the live gold eval can't run.
- [ ] 🟡 **Review the Tiresias gold set and column-doc claims** — skim `evals/tiresias_gold.yaml` (24 drafted questions: are the "answer" ones really answerable from the marts, and the "abstain" ones really not?), and check the 17 claims in `TIRESIAS.md` → "Column-doc claims to check against the data" (each says what query confirms it). Edit `models/marts/schema.yml` directly or note corrections for Claude.
- [ ] 🔴 **Approve merging the `tiresias` PR** (merge = deploy on Railway). Safe before the key exists: without it the page only shows a notice.

