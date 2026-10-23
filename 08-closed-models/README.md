# 08 - Closed Models: Gemini Fine-Tuning + Claude Comparison

Real supervised fine-tuning of a closed model (`gemini-3.1-flash-lite` on Vertex AI)
on the same support-ticket classification task from S7, compared against Claude
Haiku 5.5 (prompt + few-shot) and the three Qwen conditions from S7 (base,
few-shot, LoRA), on the same frozen 30-case test split.

| Topic | Key concepts |
|---|---|
| Closed-model fine-tuning on Google Cloud | Vertex AI supervised tuning, tuned-model endpoints, cross-provider comparison (open vs. closed), cost/quality/control trade-offs |

## Task

Same classification task as [`07-open-models`](../07-open-models): a support
ticket into `categoria` / `prioridad` / `respuesta`, same frozen 240/30/30
train/validation/test split from S7. See
[`docs/experimento.md`](docs/experimento.md) for the full protocol.

## What I did

1. **Google Cloud project**: no course-provided lab was available, so this
   runs on my own personal Google Cloud project (`thepower-s8-gemini-512218`),
   funded with a new-account $300 free trial credit. Billing, bucket, and IAM
   were all set up and torn down by me, not a shared course environment.
2. **Data conversion**: `scripts/convertir_gemini.py` converts the frozen S7
   train/validation/test splits to Gemini's `contents`/`parts` JSONL format,
   keeping an `ids.json` mapping back to the original S7 IDs. Test is never
   uploaded or used for tuning.
3. **Fine-tuning**: real supervised tuning job on Vertex AI, base model
   `gemini-3.1-flash-lite`, region `europe-west4`, adapter size 8, 2 epochs,
   same instructions as the base condition. Receipt and final job state are
   in `resultados/s8-20261020T205504/estado-final.json`.
4. **Evaluation**: six conditions on the same frozen 30-case test split, same
   validator, no JSON repair or retries — Qwen base / few-shot / LoRA (reused
   from S7, identical data and protocol) plus Gemini base / Gemini tuned /
   Claude Haiku 5.5 with the same four S7 few-shot examples.

## Results (30-case test set)

| Condition | JSON valid | Schema valid | Category correct | Priority correct | **Both correct** | Median latency |
|---|---:|---:|---:|---:|---:|---:|
| Qwen base | 30/30 | 30/30 | 14/30 | 6/30 | 3/30 | 1.51s |
| Qwen + 4 few-shot | 30/30 | 27/30 | 15/30 | 20/30 | 11/30 | 1.32s |
| **Qwen + LoRA** (S7) | 30/30 | 30/30 | 28/30 | 29/30 | **28/30** | 2.35s |
| Gemini base | 30/30 | 30/30 | 26/30 | 30/30 | 26/30 | 1.42s |
| Gemini tuned | 30/30 | 30/30 | 25/30 | 30/30 | 25/30 | 2.23s |
| Claude Haiku 5.5 + few-shot | 30/30 | 30/30 | 25/30 | 30/30 | 25/30 | 1.08s |

My own locally fine-tuned 0.6B model outperforms both closed-model conditions
on this specific task, despite Gemini being a far more capable base model
out of the box (26/30 vs. Qwen base's 3/30). Gemini's fine-tuning run did not
improve on its own base — the one point it lost is entirely in category
classification; priority was already 30/30 before and after tuning. With an
already-strong base model and a small, narrow synthetic dataset (240 rows
from 40 base situations with 6 prefix variants, 60,286 billable training
tokens), there was little headroom left to gain, and some risk of overfitting
to the training set's specific patterns rather than reinforcing general
judgment.

## Which one would I choose?

For this specific task (closed four-category classification with a fixed
JSON format, low volume, and the data I measured), I'd choose my Qwen +
LoRA, because it got the most correct answers (28/30, versus 25-26/30 for
the closed models). This choice depends on context, though. Running the
model on my own machine isn't literally free — it has a real cost, even if
in my case it's already sunk. What would actually change my decision are
task complexity and scale. By complexity I mean a task that requires more
open-ended reasoning or longer responses, not just picking between four
fixed categories. By scale I mean having to serve far more requests than my
own machine could handle at once. Either one on its own would justify
switching to a closed model via API, while still weighing the cost of that
switch. There's also a control factor the table doesn't capture: with my
Qwen + LoRA I keep the weights, can audit them, and can move them elsewhere
without depending on anyone; neither the tuned Gemini nor Claude let me
download or inspect the model, and I'd be subject to whatever that provider
decides about price and availability.

## Cost

- **Gemini tuning**: 60,286 billable training tokens, ~$0.18 at the
  supervised-tuning rate for `gemini-3.1-flash-lite` (~$3/MTok) current as
  of October 2026 — not an invoice line item, since Vertex AI's API doesn't
  return a billed amount directly; verify against actual Cloud Billing for
  an exact figure.
- **Gemini inference** (base + tuned, 60 test calls + demo): not returned by
  the API either; left as `null` in the raw results, per the exercise's own
  protocol for undisclosed costs.
- **Claude Haiku 5.5** (30 test calls + demo, few-shot): $0.0033, computed
  from measured tokens at $0.10 / $0.50 per MTok (in/out).
- **Qwen + LoRA**: no marginal cost — local inference on already-owned
  hardware (see [`07-open-models`](../07-open-models) for training cost/time).

## Configuration (no secrets)

- Project: `thepower-s8-gemini-512218` (personal Google Cloud project, not
  course-provided)
- Bucket: `thepower-s8-gemini-512218-tuning`, `europe-west4`, private,
  uniform access
- Training region: `europe-west4`; serving region: `eu`
- Tuning job: `projects/183729570563/locations/europe-west4/tuningJobs/2510795343885500416`
- Tuned endpoint: `projects/183729570563/locations/eu/endpoints/4602397344195936256`

Full job receipt: `resultados/s8-20261020T205504/estado-final.json`. Full
results: `resultados/s8-20261020T205504/informe/`.

## Reproducing this

```powershell
uv venv --python 3.12 .venv --prompt closed-models-master-project
uv pip sync --python .venv requirements.lock
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
# fill in .env: ANTHROPIC_API_KEY, GOOGLE_CLOUD_PROJECT, TUNING_BUCKET, GEMINI_SERVING_LOCATION

python scripts/convertir_gemini.py
python scripts/gemini_tuning.py preparar --proyecto $env:GOOGLE_CLOUD_PROJECT --bucket $env:TUNING_BUCKET
python scripts/gemini_tuning.py subir-datos --proyecto $env:GOOGLE_CLOUD_PROJECT --bucket $env:TUNING_BUCKET --presupuesto-usd 5 --coste-estimado-usd 1
python scripts/gemini_tuning.py crear --proyecto $env:GOOGLE_CLOUD_PROJECT --bucket $env:TUNING_BUCKET --presupuesto-usd 5 --coste-estimado-usd 1
python scripts/gemini_tuning.py estado --proyecto $env:GOOGLE_CLOUD_PROJECT --job <job-id>

python scripts/evaluar_remotos.py --condicion gemini_base --split test --salida resultados/s8/gemini_base.jsonl
python scripts/evaluar_remotos.py --condicion gemini_ajustado --modelo <endpoint> --split test --salida resultados/s8/gemini_ajustado.jsonl
python scripts/evaluar_remotos.py --condicion claude_prompt --split test --salida resultados/s8/claude_prompt.jsonl
python scripts/resumir.py --carpeta resultados/s8 --destino resultados/s8/informe
```

Requires a Google Cloud project with billing enabled (own account, not
course-provided — see Configuration above) and an Anthropic API key with
balance loaded.

## Attribution

Starting code, data, and protocol are from the AI Engineer program (thePower),
Session 8 exercise — imported from
[JoseAntonioNuevo/thepower-modelos](https://github.com/JoseAntonioNuevo/thepower-modelos)
(MIT licensed), trimmed to only the files this exercise needs. Environment
setup, the Google Cloud project, the real fine-tuning run, evaluation, and
this write-up are my own work; see the git history for the exact split
between imported scaffold and my own commits.

## License

Code/data imported from the course repo: MIT.
