# DataPilot V6: verified-result GRPO for NL-to-SQL on a 3.35B Aya model

**One-line claim:** GRPO with an executed-SQL, verified-result reward raised execution accuracy on held-out question instances from **60.8% to 82.4%** (paired McNemar p = 0.001, n = 51) on a synthetic business database, with **no statistically distinguishable change** on unseen query shapes (35.3% to 47.1%, n = 17, p = 0.625).

## Tracks and problem statements

- **Track 3**, **Problem 6: Data and Database Agents**

## Abstract

DataPilot V6 is a natural-language-to-SQL agent for business databases. We post-train Tiny Aya Global (3.35B) with GRPO and LoRA on a single 16 GB T4, using a reward that is computed by actually executing the model's SQL on a read-only SQLite connection and comparing the result set to a gold query's result set (1.0 for the same result, 0.1 for valid but wrong SQL, 0.0 for invalid or non-SELECT SQL). The benchmark is a synthetic business database (customers, products, orders, order_items) with 218 template-generated question and gold-SQL pairs, split into 150 train, 51 held-out instances of trained query shapes (`test_iid`), and 17 questions from four query shapes never seen in training (`test_novel`). A leak check (exact question and SQL match, plus template overlap) found zero overlaps.

Under identical greedy decoding and the same scorer, execution accuracy on `test_iid` rose from 0.608 (95% CI 0.471 to 0.745) to 0.824 (0.725 to 0.922); the paired difference is +21.6 points (95% bootstrap CI +11.8 to +33.3; 11 questions fixed, 0 broken; McNemar p = 0.001). Valid-SQL rate rose from 94.1% to 100%. On `test_novel`, accuracy moved from 0.353 to 0.471, but with n = 17 the paired CI (-11.8 to +35.3 points) includes zero, and valid-SQL rate fell from 100% to 94.1%, so we do not claim improvement there. The results come from one training run with one seed on a synthetic database, so they show that a verified-result reward can teach a small model a database's conventions; they do not show general text-to-SQL ability.

## Headline before to after

| Split | n | Base accuracy (95% CI) | Tuned accuracy (95% CI) | Paired diff (95% CI) | McNemar p | Valid SQL base to tuned |
|---|---|---|---|---|---|---|
| `test_iid` | 51 | 0.608 (0.471 to 0.745) | **0.824** (0.725 to 0.922) | +0.216 (+0.118 to +0.333) | 0.001 | 0.941 to 1.000 |
| `test_novel` | 17 | 0.353 (0.118 to 0.588) | 0.471 (0.235 to 0.706) | +0.118 (-0.118 to +0.353) | 0.625 | 1.000 to 0.941 |

Accuracy is execution accuracy: the generated SQL must run and return the same set of rows as the gold SQL (row order ignored). Higher is better. Base-only-correct vs tuned-only-correct counts: `test_iid` 0 vs 11, `test_novel` 1 vs 3.

**Base model + method in one line:** Tiny Aya Global (3.35B) + LoRA (r=16) trained with GRPO (TRL 1.7.1) against an executed-SQL verified-result reward.

## Problem statement and approach

Business users ask questions in plain language and need correct answers from a database. A model that writes plausible but wrong SQL is worse than no model. We treat correctness as something that can be checked mechanically: run the query, compare the rows. That check is the reward, so no learned judge is involved.

1. Build a database and a bank of question and gold-SQL pairs (`build_dataset.py`).
2. Score every generated query with one shared function (`common.py`): extract the first ```sql block, allow only a single `SELECT`, execute on a read-only connection (`mode=ro`, with a 2 second runaway-query cutoff), compare sorted result rows to the gold result.
3. Measure the base model, run GRPO (`train_grpo.py`), measure the tuned model with the same script and decoding (`eval.py`).

### Why this problem / real use case

Database agents fail silently when SQL is valid but semantically wrong. Execution-verified rewards are cheap, objective and hard to argue with, and a small model that fits on one T4 can be deployed where data cannot leave the premises.

## Hackathon repos (kits) used

**AgentTune 1.1.3.** Used in the earlier DataPilot V6 agent project (a 195-cell Colab notebook) to: (1) build a question-bound, read-only `execute_sql` tool on AgentTune's `BaseTool` / `ToolResult` classes that validates and executes SQL for one business question; (2) wire rollouts with `create_rollout_fn`; and (3) inspect and wire the agentic GRPO trainer path (`create_agentic_trainer`, TRL backend `TrlAgenticGrpo`, TRL 1.7.1). The AgentTune GRPO run did not leave a saved model or optimizer state, so it produced no results. **No number in this write-up comes from AgentTune.**

**AuditKIT.** **Not used to produce any result in this submission.** The project notebook imports no AuditKIT code; the name appears only in the recovered project's configuration and file listings. All evaluation here is done by `eval.py` (execution accuracy, bootstrap CIs, McNemar test). The author believes AuditKIT may have been run in an earlier session, but no AuditKIT output was preserved, so nothing from it is claimed or reported.

## How the repos connect

`build_dataset.py` writes `data/business.db`, `train.jsonl`, `test_iid.jsonl`, `test_novel.jsonl` and a leak report. `common.py` is imported by both `train_grpo.py` (as the reward) and `eval.py` (as the metric), so training and evaluation use the same scoring logic. `eval.py` is run twice (`TAG=base`, then `TAG=tuned ADAPTER=<checkpoint>`) and writes per-question trajectories and a summary. The reported pipeline does not route through AgentTune or AuditKIT. The read-only, result-verifying SQL execution in `common.py` is the same idea as the question-bound SQL tool built with AgentTune for the DataPilot V6 agent. Plugging the post-trained adapter into AgentTune's tool-calling rollout loop, and evaluating the resulting agent, is future work.

## Models and licenses

- **Base model:** `CohereLabs/tiny-aya-global` (Tiny Aya Global, 3.35B), loaded in fp16 on a T4. The base model is gated; the author was granted access for **non-commercial use only**. Exact terms are on the base model's page on Hugging Face and are not reproduced here. The adapter in this submission is a derivative of that model and is released under the same non-commercial restriction.
- **Adapter:** LoRA, r=16, alpha=32, dropout 0.05, target modules `all-linear`. Published at `Yogi016/datapilot-v6-tiny-aya-sql-grpo-lora`.
- No teacher model and no closed-model baseline were used.

## Datasets, benchmarks and licenses

- **Source:** fully synthetic, generated by `build_dataset.py` with a fixed seed (0). The database has 60 customers, 30 products, 400 orders and their order items. Questions are generated from 22 templates by filling in parameters (cities, categories, statuses, years, product and customer names, thresholds). Every gold SQL was executed, and pairs with empty or trivial results (no rows, `0` or `NULL`) were dropped.
- **Languages:** English only.
- **Splits:** 150 train, 51 `test_iid` (held-out parameter combinations of 18 training templates), 17 `test_novel` (four templates, T12, T15, T17, T18, that never appear in training: per-customer counts with a left join, customers without orders, products never ordered, top spender).
- **Leak check:** exact match on whitespace-normalised, lower-cased question and gold SQL between train and each test set, plus template-id overlap. Result: 0 question overlaps, 0 SQL overlaps, 0 template overlaps for `test_novel` (`data/leak_report.json`). We did not run embedding-based or MinHash checks; questions from the same template differ only in a parameter, so near-duplicates are present by construction between train and `test_iid`.
- **Licenses:** code is MIT (`LICENSE`). The synthetic benchmark (`datapilot-v6-sql-benchmark`) is CC BY 4.0. The evaluation trajectories and logs contain outputs of the non-commercial base model and are provided for research use only, under the base model's terms.

Dataset repos: `Yogi016/datapilot-v6-sql-benchmark`, `Yogi016/datapilot-v6-trajectories-and-logs`.

## Metrics, and why these

- **Execution accuracy** (higher is better): the objective we trained for and the only one that tells a user whether the answer is right.
- **Valid-SQL rate** (higher is better): separates "wrote runnable SQL" from "got the semantics right".
- **95% bootstrap CIs** per model and for the paired difference, and an exact McNemar test, because both models answer the same questions.
- **Not measured:** tool-call accuracy, latency, a general-capability benchmark, and a safety or over-refusal benchmark. The scorer is programmatic, so there is no automatic judge to validate.

## Method and experiments

- **Training setup:** TRL 1.7.1 `GRPOTrainer`, PEFT LoRA. fp16 (T4 has no bf16). 8 generations per prompt, per-device batch 8, gradient accumulation 4 (about 4 prompts per optimizer step), max completion length 128, learning rate 2e-5, 120 steps (about 3.2 epochs over 150 prompts), seed 0, chat-template prompts. A checkpoint with optimizer state was pushed to the Hub every 20 steps.
- **Reward:** 1.0 same result set as gold; 0.1 valid SELECT with a different result; 0.0 invalid, non-SELECT or multi-statement SQL.
- **Evaluation:** greedy decoding, max 160 new tokens, same prompts and scorer for base and tuned.
- **Compute:** one Nvidia T4 (16 GB) on a Hugging Face Space. Training took about 5 h 23 min, peak GPU memory 14.1 GB. Cost: about $4.30 of Hugging Face credit (a $20 credit with $15.70 remaining afterwards); earlier Colab sessions are not included.
- **Seeds / ablations:** one seed, no ablations.

## Results

See the table above. The training log (`trainer_state.json`) is in `Yogi016/datapilot-v6-trajectories-and-logs` under `logs/`. The final reported training loss (about 1e-4) is not informative for GRPO and is not evidence of improvement; the evaluation numbers are.

### Sample inputs and outputs

Three `test_iid` questions the tuned model fixed (the first three found by a scripted search, not a systematic error analysis):

- *"How many orders with status 'Delivered' were placed in 2025?"* The base model used `YEAR(order_date) = 2025`, which SQLite does not support. The tuned model used `strftime('%Y', order_date) = '2025'` and returned the right count.
- *"What is the total quantity of items ordered by customers in Kolkata?"* and the same question for Jaipur. The base model returned grouped rows (one per customer or order) instead of one total. The tuned model returned a single `SUM(quantity)` and matched the gold result.

Full per-question outputs for both models: `results/base_trajectories.jsonl` and `results/tuned_trajectories.jsonl`.

### Findings

- **Dialect and output-shape conventions were learned.** In the examples we inspected, the fixes were SQLite dialect (`strftime` instead of `YEAR`) and returning the shape the question asks for (a scalar, not grouped rows). That is useful for a deployed database agent, but it is closer to learning one database's conventions than to a general improvement in SQL reasoning.
- **No reliable gain on unseen query shapes.** 17 questions cannot separate a small real effect from noise.

### What didn't work / negative results

- `test_novel` valid-SQL rate fell from 100% to 94.1% (one invalid answer).
- The rollout log written during training (`logs/trajectories.jsonl`) was lost when the compute container restarted before it was uploaded. The per-step training log, the base and tuned evaluation trajectories, the benchmark and the code were preserved.
- An earlier GPU training run, before this one, did not save model or optimizer state and produced no usable model. This run pushes full checkpoints to the Hub every 20 steps.

## Limitations

- **Synthetic data and templates.** The database and questions are generated, not collected from real users, and `test_iid` shares query shapes with training. The result shows learning of this database and these shapes.
- **Small test sets.** 51 and 17 questions; `test_novel` is inconclusive.
- **One run, one seed**, no ablation of the reward or hyperparameters.
- **Order-insensitive result matching** can accept a query that returns the right rows in a different order than the question implies.
- **No retention checks.** We did not measure general capability, safety or over-refusal before and after.
- **No real multi-step agent evaluation.** We evaluate single-turn SQL generation, not tool-call accuracy, recovery from errors or latency.

## With more credits

- Run several seeds and report the spread.
- Add a held-out real schema and questions written by people, to test generalisation beyond templates.
- Add more query shapes to `test_novel` so it can detect a real effect.
- Train and evaluate a multi-turn agent loop that can run, inspect and repair its own queries, with tool-call accuracy and latency reported.
- Ablate the reward (the 0.1 partial credit, result-set matching variants).
- Check general-capability and safety retention.

We have not measured the effect of any of these; we do not forecast numbers.

## Artifacts

- **GitHub repo:** https://github.com/Yogendra-A/datapilot-v6
- **HF model collection:** https://huggingface.co/collections/Yogi016/datapilot-v6-models-6af89a0fc0f1dc548b7e13bb . Contains `Yogi016/datapilot-v6-tiny-aya-sql-grpo-lora`.
- **HF dataset collection:** https://huggingface.co/collections/Yogi016/datapilot-v6-datasets-6af89a0f03be12bf9abc75f3 . Contains `Yogi016/datapilot-v6-sql-benchmark` and `Yogi016/datapilot-v6-trajectories-and-logs`.


## Documentation and reproduction

**Environment:** Python 3.12, one GPU with 16 GB (we used a T4), `trl==1.7.1`, `peft`, `transformers`, `datasets`, `accelerate`, `huggingface_hub`. On our image an old preinstalled `torchao` conflicted with transformers and was removed with `pip uninstall -y torchao`. You need a Hugging Face login that can read `CohereLabs/tiny-aya-global` (accept the model's license on its page first) and, for training, write to your own repo.

```bash
pip install -U "trl==1.7.1" peft datasets transformers accelerate huggingface_hub
pip uninstall -y torchao
python build_dataset.py                                  # data/ + leak_report.json
TAG=base python eval.py                                  # expect 0.608 (iid) and 0.353 (novel)
HUB_ID=<you>/<your-adapter-repo> python train_grpo.py    # about 5.5 h on a T4; RESUME=1 to continue
TAG=tuned ADAPTER=grpo_out python eval.py                # tuned numbers; adapter on the Hub also works
```

### Repo layout

- `build_dataset.py`: synthetic DB, question/gold pairs, splits, leak check
- `common.py`: read-only SQL execution and the verified-result scorer (shared by training and eval)
- `train_grpo.py`: LoRA GRPO training with Hub checkpointing and resume
- `eval.py`: execution accuracy with bootstrap CIs, per-question trajectories
- `results/`: `base_summary.json`, `tuned_summary.json`, per-question trajectories
- `logs/`: `trainer_state.json`, the per-step GRPO training log
- `frontend/`: React chat front end for DataPilot V6 (has its own README)
- `docs/kits_report.txt` and `tools/kits_report.py`: the scan of the earlier DataPilot notebook used to document AgentTune and AuditKIT usage
- `requirements.txt`: Python dependencies for the scripts

### Declaration of work done outside the hackathon

**What existed before the final-day work:** the DataPilot V6 agent project (AgentTune adapter, question-bound read-only SQL tool, rollout wiring, React front end). The recovered project configuration is timestamped 2026-11-07. We declare conservatively: all DataPilot V6 agent and front-end work completed before 2026-11-14 counts as prior work, and was not built for this write-up. **What was built on 2026-11-14:** everything in `build_dataset.py`, `common.py`, `train_grpo.py` and `eval.py`, and every number in this write-up.

### LLM usage statement

The dataset, training and evaluation scripts and the draft of this write-up were largely written with Claude (Anthropic) assistance, and the results were produced by running them. Most of the code and text (the large majority) was generated with Claude; the author ran, debugged and verified all experiments on their own accounts and hardware, and checked the reported numbers against the output files.

## Teammates tagged

Solo submission: Yogendra A (GitHub: Yogendra-A, Hugging Face: Yogi016) did all of the work: data design decisions, running every experiment, and the submission.
