# 07 - Open Models: LoRA Fine-Tuning

Fine-tuning an open-weight model (`Qwen/Qwen3-0.6B`) with LoRA to classify
synthetic educational-platform support tickets into a JSON object
(`categoria`, `prioridad`, `respuesta`), compared against prompting-only
baselines on the same model.

| Topic | Key concepts |
|---|---|
| LoRA fine-tuning of an open-weight LLM | Supervised fine-tuning, LoRA adapters, prompting vs. few-shot vs. fine-tuning, frozen train/val/test protocol, model card publishing |

## Task

Classify a fictional support ticket into:

```json
{
  "categoria": "facturacion",
  "prioridad": "media",
  "respuesta": "Indica el concepto y la fecha del pago para revisar la incidencia de facturación."
}
```

- `categoria`: `acceso`, `facturacion`, `tecnico`, or `consulta`.
- `prioridad`: `alta` (explicit collective impact or exposed private data),
  `media` (one person blocked, or a billing problem), `baja` (everything else).
  The word "urgente" alone must **not** raise priority — this rule is tested
  explicitly in the data (see Error analysis below).
- `respuesta`: one or two honest sentences; no fabricated promises, no
  requesting passwords.

## What I did

1. **Environment**: Python 3.12 venv, `requirements-training.lock`
   (Transformers, TRL, PEFT, Datasets, PyTorch). On Windows, the lock resolves
   PyTorch's **CPU-only** build by default — CUDA wheels live on a separate
   index. I reinstalled `torch==2.14.1` from
   `https://download.pytorch.org/whl/cu126` to actually use my GPU
   (NVIDIA RTX 4070 Laptop).
2. **Data**: 240 train / 30 validation / 30 test synthetic tickets, frozen
   and hash-checked before training (`config/experimento-congelado.json`).
3. **Training**: LoRA adapter, fixed recipe (`r=8`, `alpha=16`, `dropout=0.05`,
   7 target projections, 2 epochs, no hyperparameter search), `scripts/entrenar_lora.py`.
4. **Evaluation**: three conditions — base model with instructions only,
   base model with 4 fixed few-shot examples, and base model + my LoRA
   adapter — all on the same frozen 30-case test split, same validator,
   no JSON repair or retries.
5. **Publishing**: adapter pushed to a private Hugging Face repo with a model
   card, then **re-downloaded from the Hub** (not from local disk) and
   queried to confirm the published version actually works.

## Results (30-case test set, greedy decoding)

| Condition | JSON valid | Schema valid | Category correct | Priority correct | **Both correct** |
|---|---:|---:|---:|---:|---:|
| Base + instructions only | 30/30 | 30/30 | 14/30 | 6/30 | **3/30** |
| Base + 4 few-shot examples | 30/30 | 27/30 | 15/30 | 20/30 | **11/30** |
| **Base + LoRA adapter** | 30/30 | 30/30 | 28/30 | 29/30 | **28/30** |

Hardware: Windows 11, NVIDIA RTX 4070 Laptop GPU, CUDA 12.6. Training took
~87 s for 2 epochs / 60 optimizer steps — about 7.5x faster than the
course's own Mac (MPS) reference run (662.9 s), useful as a hardware
comparison point, not a claim about the method itself.

Full per-case outputs are in `resultados/ensayo/*.jsonl` (kept as-is, no
repair); the aggregate report is in `resultados/ensayo/informe.*`.

## Error analysis (3 cases)

**Two ambiguous category-boundary misses by the LoRA adapter** (`resultados/ensayo/qwen_lora.jsonl`, ids `TE-21`, `TE-25`): both are tickets that don't describe a clear, blocking problem (a cosmetic UI color issue that doesn't block usage; a pure informational question about whether livestreams get recorded). All three conditions struggle with these two specific cases to some degree — they appear to be the two hardest items in the 30-case test set, not a LoRA-specific weakness.

**One rule-following failure by the base and few-shot conditions** (`TE-07`, *"Urgente: ¿puedo configurar un método de acceso adicional? No estoy bloqueado."*): the prompt explicitly states the word "urgente" alone must not raise priority. The base model raises it to `alta` anyway; the few-shot condition raises it and additionally **hallucinates `"urgente"` as a priority value**, which isn't in the allowed schema (`alta`/`media`/`baja`) — confirmed by `esquema_valido: false` on that record, even though none of the 4 few-shot examples contain that word. The LoRA adapter applies the rule correctly on this and the other 3 "Urgente:" test cases.

## Adapter

Published on the Hugging Face Hub (private repo):
**[LauraPuerto/qwen3-0.6b-support-lora](https://huggingface.co/LauraPuerto/qwen3-0.6b-support-lora)**

Model card: `modelos/lora-soporte/README.md` (uploaded alongside the weights).
Reload-from-Hub verification evidence: `material/evidencias/huggingface-recarga.json`.

## Reproducing this

```powershell
uv venv --python 3.12 .venv
uv pip sync --python .venv requirements-training.lock
uv pip install --python .venv "torch==2.14.1" --index-url https://download.pytorch.org/whl/cu126 --reinstall-package torch
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python scripts/descargar_modelo.py
python scripts/entrenar_lora.py --salida modelos/lora-soporte
python scripts/evaluar_qwen.py --condicion qwen_base --split test --salida resultados/ensayo/qwen_base.jsonl
python scripts/evaluar_qwen.py --condicion qwen_fewshot --split test --salida resultados/ensayo/qwen_fewshot.jsonl
python scripts/evaluar_qwen.py --condicion qwen_lora --split test --adaptador modelos/lora-soporte --salida resultados/ensayo/qwen_lora.jsonl
python scripts/resumir.py --carpeta resultados/ensayo --destino resultados/ensayo/informe
```

The `uv pip install ... cu126` line is only needed on Windows; see
[pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/)
for the right index on other platforms.

## Attribution

Starting code, data, and protocol are from the AI Engineer program (thePower),
Session 7 exercise — imported from
[JoseAntonioNuevo/thepower-modelos](https://github.com/JoseAntonioNuevo/thepower-modelos)
(MIT licensed), trimmed to only the files this exercise needs. Everything from
environment setup onward (training, evaluation, the published adapter, this
write-up) is my own work; see the git history for the exact split between
imported scaffold and my own commits.

## License

Code/data imported from the course repo: MIT. Base model `Qwen/Qwen3-0.6B`:
Apache-2.0.
