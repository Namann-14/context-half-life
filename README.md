# context-half-life

Code, experiments and paper source for **"The Half-Life of Context: Measuring and Repairing Context Rot in
Large Language Models"** (Nayak, Singh, Singh, Garg; Chitkara University).

Long LLM conversations accumulate stale, contradictory, redundant and irrelevant text ("context rot").
This repository implements

- the **Context Half-Life**: the age (in turns) at which a fact has a 50 % chance of no longer being
  usable by the model, estimated with survival analysis (exponential and Weibull fits, Kaplan-Meier
  curves, bootstrap confidence intervals);
- the **Rot Index** and session half-life of a whole context;
- **detectors** for the four decay modes and **repair operations** (KEEP / UPDATE / MERGE / REMOVE) with a
  protection set and verification with rollback, plus the baselines (full context, sliding window,
  rolling summary, random and oldest-first repair);
- a **rot-injection generator** that produces *synthetic* sessions with known ground truth;
- the evaluation harness (E1-E5) and the build scripts of the paper.

Repair works at the context layer only: no model is retrained.

## Status

| Part | State |
|---|---|
| Library `src/context_half_life/` | implemented, unit-tested (`pytest`) |
| E1-E5 scripts and `analyze.py` | implemented and run once with `llama3.2:3b` (reader) and `qwen2.5:3b` (judge); see `results/` |
| `results/` | raw per-call JSONL, summary CSVs and `paper_numbers.json`; every number in the paper is traced to files here |

## Layout

```
src/context_half_life/   library (probe, halflife, rot, detectors, repair, inject, niah, data, scoring, stats, llm, tokens)
experiments/             one resumable script per experiment, fetch_data.py, shared helpers
results/                 raw/*.jsonl (per-call logs), summary/*.csv, env/ (versions, model digests)
tests/                   pytest suite (no LLM needed)
paper/                   paper text, figure scripts, DOCX builder and checks (template/ = text-free IEEE template)
data/                    downloaded datasets (git-ignored)
```

## Setup

Requires Python 3.10+ (developed on 3.14) and [uv](https://docs.astral.sh/uv/).

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev,paper]"
```

On Linux/macOS use `.venv/bin/python`. Experiments use local models through
[Ollama](https://ollama.com):

```bash
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
```

Copy `.env.example` to `.env` and export what you need. **No secret is stored in the repository**; optional
hosted-model keys are read only from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

```bash
python experiments/fetch_data.py   # LongMemEval (cleaned, MIT) + public-domain Gutenberg texts
pytest                             # unit tests, no model needed
```

## Reproducing the results

Each script appends to `results/raw/<name>.jsonl` and skips work already done, so an interrupted run can be
resumed. Seeds are fixed (`context_half_life.SEED`); decoding uses temperature 0.

| Output | Command |
|---|---|
| E1 heat maps (literal vs paraphrased needle) | `python experiments/e1_niah.py --model llama3.2:3b` |
| E2 half-lives, Kaplan-Meier curves | `python experiments/e2_halflife.py --model llama3.2:3b --mode ageing` (and `--mode matched`) |
| E3 detectors, onset recovery (synthetic sessions) | `python experiments/e3_injection.py` |
| E4 repair comparison and E5 ablations (LongMemEval subset) | `python experiments/e4_repair.py --stage answer`, then `--stage judge` |
| Summary tables and `paper_numbers.json` | `python experiments/analyze.py` |
| Whole pipeline after E1/E2 | `experiments/run_light.ps1`, `experiments/run_rest.ps1` |
| Paper figures | `python paper/make_figures.py` (illustrative) and `python paper/make_result_figures.py` (measured) |
| Paper (.docx) | `python paper/make_result_figures.py`, `python paper/build_paper.py`, then `python paper/verify_output.py` |
| Paper PDF (Word, Windows) | `python paper/render_pdf.py` |

## The paper build

`paper/build_paper.py` builds the IEEE two-column document on top of `paper/template/ieee_template.docx`, a
copy of the conference template with all text, images and metadata removed (only layout, styles and
numbering remain). Code listings in the paper are extracted from the marked regions
(`# [listing:NAME]` ... `# [/listing]`) of the modules in `src/`, so the paper shows the code that ran.

## Data and licences

- Code: MIT (see `LICENSE`).
- LongMemEval (cleaned): MIT, <https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned>.
- Haystack text: public-domain books from Project Gutenberg.
- Model weights are downloaded by the user under their own licences (Llama 3.x Community License, Qwen2.5
  licence); none are redistributed here.

## Citing

See `CITATION.cff`.
