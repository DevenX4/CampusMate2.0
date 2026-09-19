# Choosing the SLM (Phase 15)

CampusMate does not depend on a model: the chat pipeline calls a `GenerationProvider`, and
which one is used is configuration (`GENERATION_PROVIDER`, `GENERATION_MODEL`,
`GENERATION_BASE_URL`). This document records how the model is chosen. **No model has been
downloaded yet**: that is the project owner's decision (download size, licence, runtime).

## What the model has to do

The model does **not** need to know anything about GUNI. The router and retrieval have
already found the evidence; the model only has to:

1. write a short answer from 1–8 numbered sources (about 1,500–3,000 prompt tokens);
2. cite the source number after each fact;
3. copy numbers, codes and names exactly;
4. say when something is synthetic demo data;
5. reply with the exact abstain sentence when the sources do not answer.

This is reading comprehension plus instruction following, which small instruction-tuned
models (1.5–4 B parameters) do reasonably well. It is not open-ended knowledge, which is
where small models fail. The grounding validator (Phase 16) checks every answer afterwards,
so a model mistake becomes an abstention instead of a false fact.

## The hardware budget (measured on this machine)

| Resource | Size | Already used by CampusMate |
|---|---|---|
| GPU | RTX 2050, **4 GB VRAM**, idle (the display runs on the integrated GPU) | nothing |
| RAM | **7.2 GB** usable | API with BGE + Chroma + BM25 ≈ 300 MB working set (630 MB committed); PostgreSQL ≈ 240 MB |
| Free RAM with the IDE, browser and other apps open | **≈ 0.6 GB** | |
| Disk | C: 31 GB free · D: 197 GB free | |

Consequences:

- **The model must fit entirely in VRAM.** If layers spill to the CPU, they use system RAM,
  which is already nearly full (the machine would swap), and they run at CPU memory speed.
- **VRAM budget:** 4 GB ≈ model weights + KV cache + about 0.3–0.5 GB of runtime buffers.
  The KV cache for a 4,096-token context is roughly 0.1–0.6 GB, depending on the model's
  attention layout (2 × layers × KV heads × head size × 2 bytes per token). So the weights
  must stay at or below about **2.5–3 GB**: a 3–4 B model quantised to 4 bits (Q4_K_M), or
  a smaller one.
- **Speed (an estimate, to be measured):** generating each token reads every weight once,
  so speed is limited by memory bandwidth. The RTX 2050 (64-bit GDDR6) has about 112 GB/s,
  which gives a theoretical ceiling of about 112 / model-GB tokens per second: about 45 tok/s
  for a 2.5 GB model and about 100 for a 1 GB model. Real throughput is usually 50–70% of the
  ceiling. A 150-token answer should therefore take roughly 3–7 s plus 1–2 s to read the
  prompt. `python -m app.generation check --probe` prints the real numbers.
- **Models go on D:.** Set `OLLAMA_MODELS=D:\ollama\models` before downloading.

## Candidates (4-bit GGUF, all fit the budget)

| Model | Params | Licence | ~Q4_K_M size | Notes |
|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | 1.5 B | Apache-2.0 | 1.0 GB | Fastest; the smallest model worth trying for cited answers |
| Qwen2.5-3B-Instruct | 3.1 B | Qwen Research (non-commercial) | 1.9 GB | Strong for its size; the licence restricts commercial use |
| Llama-3.2-3B-Instruct | 3.2 B | Llama 3.2 Community | 2.0 GB | Good instruction following; acceptable-use policy applies |
| Phi-4-mini-instruct | 3.8 B | MIT | 2.5 GB | Strong reasoning for its size; tight fit |
| Qwen3-4B-Instruct-2507 | 4.0 B | Apache-2.0 | 2.5 GB | Non-thinking variant (no hidden reasoning tokens, lower latency); tight fit |
| Gemma-3-4B-it | 4.3 B | Gemma Terms of Use | 3.3 GB in Ollama (includes the vision encoder) | Probably too tight with the KV cache |
| SmolLM2-1.7B-Instruct | 1.7 B | Apache-2.0 | 1.1 GB | Weaker at following instructions |

Excluded: 7–8 B models (about 4.5 GB at Q4, which does not fit in 4 GB), and anything that
needs CPU offload. Sizes are approximate: check the model page before downloading. Newer
small models may have appeared since this list was written; changing to one only means
changing `GENERATION_MODEL`.

**Recommended shortlist:** three models from different size and family points, about 6 GB of
downloads in total:

1. **Qwen2.5-1.5B-Instruct**: the speed floor. If it passes, it is the cheapest answer.
2. **Qwen3-4B-Instruct-2507**: the strongest Apache-licensed model that fits.
3. **Phi-4-mini-instruct** (MIT) or **Llama-3.2-3B-Instruct**: a second family, so the
   result is not one vendor's quirk.

## Runtime

| Option | For | Against |
|---|---|---|
| **Ollama** (recommended) | Windows installer; bundles CUDA; manages models; OpenAI-compatible API at `127.0.0.1:11434/v1`; listens only on localhost by default | A background service; less control over options |
| llama.cpp `llama-server` | One binary (CUDA build); full control (`-ngl 99 -c 4096 --alias <name>`) | Manual downloads and start-up |
| Hosted API (any OpenAI-compatible) | Best quality; uses no local resources | Questions and evidence leave the machine; needs an API key, internet and money; does not fit the local-only goal |
| In-process (llama-cpp-python, transformers) | No extra process | Rejected: fragile CUDA builds on Windows, and a model crash or OOM would take the API down |

All the local options and the hosted option use the **same provider class**
(`OpenAICompatibleProvider`); only the configuration differs.

## How the models will be compared (Phase 16 onwards)

The same answer evaluation runs for `extractive` and for each candidate, on the 58 dataset
questions:

- **answer correctness:** the key facts of `expected_answer` (numbers, codes, names) appear;
- **grounding:** the share of answers that pass the validator (every fact supported by a cited
  source);
- **citation validity:** the cited numbers exist, and the cited sources contain the fact;
- **abstention:** category H is refused, and answerable questions are not;
- **synthetic labelling:** synthetic facts are presented as demo data;
- **cost:** latency p50/p95, tokens/s, peak VRAM (`nvidia-smi`).

Choose the **smallest model that meets the quality bar**. A bigger model is only worth its
latency and VRAM if it measurably answers better.

## Baseline: the extractive provider (no model)

`GENERATION_PROVIDER=extractive` (the default) answers by copying the most relevant
sentences, with citations. It cannot invent anything, and it labels synthetic information.
Its limits are the reasons an SLM is wanted:

- it cannot rephrase or combine facts;
- it misses paraphrases: "teaches" does not match "taught_by", and "exams" does not match
  "examinations";
- it cannot notice that a relevant-looking sentence does not actually answer the question.
