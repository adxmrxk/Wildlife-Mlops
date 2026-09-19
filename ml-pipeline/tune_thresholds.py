"""Tune a per-class logit bias directly for macro-F1 (coordinate ascent).

Prior-based logit adjustment failed because the 3.37x imbalance is too mild to
explain dog/elephant recall. This instead learns one bias per class directly
against the objective we care about, which can also correct confusions that
have nothing to do with class frequency.

Fitted on one split, reported on a disjoint split.
"""
import json, sys
from pathlib import Path
import torch
from PIL import Image
sys.path.insert(0, '/app')
from src.training.trainer import WildlifeModel
from src.inference.predictor import Predictor

VAL = Path('/app/data/val')
PER = int(sys.argv[1]) if len(sys.argv) > 1 else 60
mapping = {int(k): v for k, v in json.load(open('/app/data/species_mapping.json')).items()}
classes = [mapping[i] for i in sorted(mapping)]
K = len(classes)

p = Predictor(model_path='/app/models/wildlife_model_resnet50.pt',
              species_mapping=mapping, device='cpu')
p.load_model(WildlifeModel)

print(f"Collecting logits ({PER}/class)…")
logits, labels = [], []
for idx, name in sorted(mapping.items()):
    for f in sorted((VAL / name).glob('*'))[:PER]:
        t = p.transforms(Image.open(f).convert('RGB')).unsqueeze(0)
        with torch.no_grad():
            logits.append(p.model(t).squeeze(0))
        labels.append(idx)
logits = torch.stack(logits); labels = torch.tensor(labels)
print(f"  {len(labels)} images")

g = torch.Generator().manual_seed(0)
perm = torch.randperm(len(labels), generator=g)
half = len(labels) // 2
fit_i, ev_i = perm[:half], perm[half:]


def scores(lg, lb, bias):
    pred = (lg + bias).argmax(1)
    acc = pred.eq(lb).float().mean().item()
    recs, f1s, precs = [], [], []
    for i in range(K):
        tp = ((pred == i) & (lb == i)).sum().item()
        act = (lb == i).sum().item()
        prd = (pred == i).sum().item()
        rec = tp / act if act else 0.0
        pre = tp / prd if prd else 0.0
        recs.append(rec); precs.append(pre)
        f1s.append(2 * pre * rec / (pre + rec) if (pre + rec) else 0.0)
    return acc, sum(recs) / K, sum(f1s) / K, recs, precs


fl, fb = logits[fit_i], labels[fit_i]
bias = torch.zeros(K)
best = scores(fl, fb, bias)[2]          # optimise macro-F1
GRID = [round(-2.0 + 0.1 * i, 2) for i in range(41)]
for _ in range(4):                       # a few sweeps to convergence
    improved = False
    for c in range(K):
        cur = bias[c].item()
        for v in GRID:
            bias[c] = v
            s = scores(fl, fb, bias)[2]
            if s > best + 1e-6:
                best, cur, improved = s, v, True
        bias[c] = cur
    if not improved:
        break

print(f"\nFitted per-class bias (macro-F1 on fit split: {best:.4f})")
for c, b in zip(classes, bias.tolist()):
    if abs(b) > 1e-9:
        print(f"    {c:<10} {b:+.2f}")

el, eb = logits[ev_i], labels[ev_i]
a0, r0, f0, rec0, pre0 = scores(el, eb, torch.zeros(K))
a1, r1, f1_, rec1, pre1 = scores(el, eb, bias)

print(f"\nHELD-OUT ({len(ev_i)} images the fit never saw)")
print(f"  accuracy         : {a0:.4f} -> {a1:.4f}  ({100*(a1-a0):+.2f} pts)")
print(f"  balanced accuracy: {r0:.4f} -> {r1:.4f}  ({100*(r1-r0):+.2f} pts)")
print(f"  macro F1         : {f0:.4f} -> {f1_:.4f}  ({100*(f1_-f0):+.2f} pts)")
print(f"\n  {'class':<10} {'recall':>16}   {'precision':>16}")
for i in sorted(range(K), key=lambda i: rec0[i]):
    d = rec1[i] - rec0[i]
    mark = '  <-- improved' if d > 0.02 else ('  <-- regressed' if d < -0.02 else '')
    print(f"  {classes[i]:<10} {rec0[i]:.3f} -> {rec1[i]:.3f}   {pre0[i]:.3f} -> {pre1[i]:.3f}{mark}")

print("\nBIAS_JSON=" + json.dumps({c: round(b, 4) for c, b in zip(classes, bias.tolist())}))
