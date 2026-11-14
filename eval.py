import json
import os
import random

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import extract_sql, load_jsonl, score, to_messages

MODEL = os.environ.get("MODEL", "CohereLabs/tiny-aya-global")
ADAPTER = os.environ.get("ADAPTER")
TAG = os.environ.get("TAG", "base")
BATCH = int(os.environ.get("EVAL_BATCH", 8))
MAX_NEW = int(os.environ.get("MAX_NEW", 160))
os.makedirs("results", exist_ok=True)

tok = AutoTokenizer.from_pretrained(MODEL)
tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float16, device_map="auto")
if ADAPTER:
    model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()


def generate(prompts):
    texts = [tok.apply_chat_template(to_messages(p), add_generation_prompt=True, tokenize=False)
             for p in prompts]
    enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False,
                             pad_token_id=tok.pad_token_id)
    return [tok.decode(o[enc["input_ids"].shape[1]:], skip_special_tokens=True) for o in out]


def bootstrap_ci(xs, n=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


summary = {"tag": TAG, "model": MODEL, "adapter": ADAPTER, "decoding": "greedy",
           "max_new_tokens": MAX_NEW}
with open(f"results/{TAG}_trajectories.jsonl", "w") as tf:
    for split in ["test_iid", "test_novel"]:
        rows = load_jsonl(f"data/{split}.jsonl")
        correct, valid = [], []
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            outs = generate([r["prompt"] for r in chunk])
            for r, o in zip(chunk, outs):
                _, v, c = score(o, r["gold_sql"])
                correct.append(1.0 if c else 0.0)
                valid.append(1.0 if v else 0.0)
                tf.write(json.dumps({"split": split, "template_id": r["template_id"],
                                     "question": r["question"], "gold_sql": r["gold_sql"],
                                     "generated": o, "extracted_sql": extract_sql(o),
                                     "valid_sql": v, "correct": c}) + "\n")
        lo, hi = bootstrap_ci(correct)
        summary[split] = {"n": len(rows), "execution_accuracy": sum(correct) / len(rows),
                          "ci95": [lo, hi], "valid_sql_rate": sum(valid) / len(rows)}
        print(split, summary[split])

with open(f"results/{TAG}_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("EVAL DONE", TAG)
