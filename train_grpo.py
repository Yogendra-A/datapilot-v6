import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM
from trl import GRPOConfig, GRPOTrainer

from common import load_jsonl, score, to_messages

MODEL = os.environ.get("MODEL", "CohereLabs/tiny-aya-global")
HUB_ID = os.environ.get("HUB_ID", "Yogi016/datapilot-v6-tiny-aya-sql-grpo-lora")
OUT = os.environ.get("OUT", "grpo_out")
MAX_STEPS = int(os.environ.get("MAX_STEPS", 120))
SAVE_STEPS = int(os.environ.get("SAVE_STEPS", 20))
NUM_GEN = int(os.environ.get("NUM_GENERATIONS", 8))
MAX_COMPLETION = int(os.environ.get("MAX_COMPLETION", 128))
os.makedirs("logs", exist_ok=True)

rows = load_jsonl("data/train.jsonl")
train_ds = Dataset.from_list([
    {"prompt": to_messages(r["prompt"]), "question": r["question"], "gold_sql": r["gold_sql"]}
    for r in rows
])

_calls = {"n": 0}


def reward_exec(prompts, completions, gold_sql, question=None, **kwargs):
    _calls["n"] += 1
    rewards = []
    with open("logs/trajectories.jsonl", "a") as f:
        for i, (comp, gold) in enumerate(zip(completions, gold_sql)):
            text = comp if isinstance(comp, str) else comp[0]["content"]
            r, valid, correct = score(text, gold)
            rewards.append(r)
            f.write(json.dumps({
                "reward_call": _calls["n"],
                "question": question[i] if question else None,
                "gold_sql": gold, "completion": text,
                "reward": r, "valid_sql": valid, "correct": correct,
            }) + "\n")
    return rewards


use_cuda = torch.cuda.is_available()
cfg = GRPOConfig(
    output_dir=OUT,
    max_steps=MAX_STEPS,
    per_device_train_batch_size=NUM_GEN,
    gradient_accumulation_steps=4,
    num_generations=NUM_GEN,
    max_completion_length=MAX_COMPLETION,
    learning_rate=2e-5,
    logging_steps=1,
    save_steps=SAVE_STEPS,
    save_total_limit=2,
    bf16=use_cuda and torch.cuda.is_bf16_supported(),
    fp16=use_cuda and not torch.cuda.is_bf16_supported(),
    report_to="none",
    push_to_hub=True,
    hub_model_id=HUB_ID,
    hub_strategy="checkpoint",
    seed=0,
)
lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
                  target_modules="all-linear")

model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16 if use_cuda else "auto")
trainer = GRPOTrainer(model=model, reward_funcs=reward_exec, args=cfg,
                      train_dataset=train_ds, peft_config=lora)

resume_path = None
if os.environ.get("RESUME") == "1":
    from huggingface_hub import snapshot_download
    try:
        p = snapshot_download(HUB_ID, allow_patterns="last-checkpoint/*")
        cand = os.path.join(p, "last-checkpoint")
        if os.path.isdir(cand):
            resume_path = cand
            print("Resuming from", cand)
    except Exception as e:
        print("No checkpoint to resume from:", e)

trainer.train(resume_from_checkpoint=resume_path)
if use_cuda:
    print(f"PEAK GPU MEMORY: {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")

with open("logs/train_log.json", "w") as f:
    json.dump(trainer.state.log_history, f, indent=1)
trainer.save_model(OUT)
trainer.push_to_hub()
print("TRAINING DONE. Adapter in", OUT, "and on", HUB_ID)
