#!/usr/bin/env python3
"""Fit a temperature-scaling parameter for the live model.

A network's softmax is usually over-confident: it reports 85% on predictions
that are right 61% of the time. Temperature scaling (Guo et al., 2017) divides
the logits by a single learned scalar T before the softmax, which leaves every
prediction unchanged but makes the reported probability honest.

Because it only rescales logits, argmax — and therefore accuracy — is
mathematically unchanged. Only the confidence numbers move.

The temperature is fitted on one half of the validation set and reported on the
other half, so the quoted improvement is measured on data the fit never saw.

Writes models/calibration.json, which the ML service loads on startup.
"""

import argparse
import json
import random
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image

from src.inference.predictor import Predictor
from src.training.trainer import WildlifeModel

BINS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]


def collect_logits(predictor, val_dir: Path, mapping: dict, per_class: int):
    """Run the model once and keep the raw logits, so fitting needs no re-inference."""
    logits, labels = [], []
    for idx, name in sorted(mapping.items()):
        class_dir = val_dir / name
        if not class_dir.is_dir():
            print(f"  warning: missing class directory {class_dir}")
            continue
        files = sorted(f for f in class_dir.iterdir() if f.is_file())
        if per_class > 0:
            files = files[:per_class]
        for f in files:
            try:
                tensor = predictor.transforms(Image.open(f).convert('RGB')).unsqueeze(0)
            except Exception:
                continue
            with torch.no_grad():
                logits.append(predictor.model(tensor).squeeze(0))
            labels.append(idx)
    return torch.stack(logits), torch.tensor(labels)


def ece(probs: torch.Tensor, labels: torch.Tensor) -> tuple:
    """Expected Calibration Error, plus the per-bin table."""
    conf, pred = probs.max(dim=1)
    correct = pred.eq(labels)
    total = len(labels)
    error = 0.0
    table = []
    for lo, hi in BINS:
        mask = (conf >= lo) & (conf < hi)
        if mask.sum() == 0:
            continue
        bin_conf = conf[mask].mean().item()
        bin_acc = correct[mask].float().mean().item()
        error += (mask.sum().item() / total) * abs(bin_conf - bin_acc)
        table.append((lo, min(hi, 1.0), int(mask.sum()), bin_conf, bin_acc))
    return error, table


def print_table(title, table):
    print(f"\n  {title}")
    print(f"    {'bin':>10} {'n':>5} {'avg conf':>9} {'accuracy':>9} {'gap':>8}")
    for lo, hi, n, c, a in table:
        print(f"    {lo:.1f}-{hi:.1f}".rjust(14) + f"{n:>6} {c:>9.3f} {a:>9.3f} {c - a:>+8.3f}")


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Learn T by minimising negative log-likelihood. Convex in 1/T; LBFGS is standard."""
    log_t = torch.zeros(1, requires_grad=True)  # optimise log T to keep T > 0
    optimizer = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_t.exp().item())


def main(args):
    mapping = {int(k): v for k, v in json.load(open(args.species_mapping)).items()}
    predictor = Predictor(model_path=args.model, species_mapping=mapping, device='cpu')
    predictor.load_model(WildlifeModel)

    print(f"Collecting logits from {args.val_dir} ({args.per_class} per class)…")
    logits, labels = collect_logits(predictor, Path(args.val_dir), mapping, args.per_class)
    print(f"  {len(labels)} images over {len(mapping)} classes")

    # Split so the reported improvement is on data the fit never saw.
    generator = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(len(labels), generator=generator)
    half = len(labels) // 2
    fit_idx, eval_idx = perm[:half], perm[half:]

    temperature = fit_temperature(logits[fit_idx], labels[fit_idx])
    print(f"\nFitted temperature: T = {temperature:.4f}")
    print("  T > 1 means the model was over-confident and probabilities are being softened.")

    held_logits, held_labels = logits[eval_idx], labels[eval_idx]
    before = F.softmax(held_logits, dim=1)
    after = F.softmax(held_logits / temperature, dim=1)

    ece_before, table_before = ece(before, held_labels)
    ece_after, table_after = ece(after, held_labels)

    acc_before = before.argmax(1).eq(held_labels).float().mean().item()
    acc_after = after.argmax(1).eq(held_labels).float().mean().item()

    print(f"\nHELD-OUT RESULTS ({len(held_labels)} images the fit never saw)")
    print_table("before calibration", table_before)
    print_table("after calibration", table_after)

    print(f"\n  accuracy before : {acc_before:.4f}")
    print(f"  accuracy after  : {acc_after:.4f}   (unchanged by design — T cannot alter argmax)")
    print(f"  mean confidence : {before.max(1).values.mean():.4f} -> {after.max(1).values.mean():.4f}")
    print(f"  ECE             : {ece_before:.4f} -> {ece_after:.4f} "
          f"({100 * (ece_before - ece_after) / max(ece_before, 1e-9):+.1f}%)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "temperature": round(temperature, 6),
        "fitted_on": str(args.val_dir),
        "images_used": int(len(labels)),
        "ece_before": round(ece_before, 6),
        "ece_after": round(ece_after, 6),
        "accuracy_held_out": round(acc_after, 6),
    }, indent=2))
    print(f"\n✓ Wrote {out}")
    print("  Restart or POST /reload on the ML service to apply it.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fit temperature scaling for the wildlife model')
    parser.add_argument('--model', default='models/wildlife_model_resnet50.pt')
    parser.add_argument('--val-dir', default='data/val')
    parser.add_argument('--species-mapping', default='data/species_mapping.json')
    parser.add_argument('--per-class', type=int, default=40,
                        help='validation images per class (0 = all)')
    parser.add_argument('--out', default='models/calibration.json')
    parser.add_argument('--seed', type=int, default=0)
    main(parser.parse_args())
