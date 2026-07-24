# Agent usage

The full agent-facing guide for this tool lives in **[SKILL.md](SKILL.md)** — it's the
canonical doc (registered as the `webgen` skill). It covers when to invoke, the
`python3 webgen.py` CLI contract, the tokens-first build loop, every flag, the
`capture` reference workflow, and the `check` quality gate.

Quick reminder of the contract: call `python3 webgen.py <verb> …`, read the
**single JSON object on stdout**, check `ok`, and **Read the screenshot paths in
`shots[*]`** — they are why the tool exists. Progress streams to stderr. See
SKILL.md for everything else.
