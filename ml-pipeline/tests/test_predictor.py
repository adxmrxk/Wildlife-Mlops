"""Tests for the Predictor class — no real model required."""

import pytest
from src.inference.predictor import Predictor


SPECIES_MAPPING = {
    0: "elephant",
    1: "lion",
    2: "giraffe",
    3: "zebra",
    4: "cheetah",
}


# ── Initialization ────────────────────────────────────────────────────────────

def test_predictor_init_defaults():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    assert predictor.model_path == "models/test_model.pt"
    assert predictor.species_mapping == SPECIES_MAPPING
    assert predictor.confidence_threshold == 0.5
    assert predictor.is_loaded is False
    assert predictor.model is None


def test_predictor_init_custom_threshold():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
        confidence_threshold=0.8,
    )
    assert predictor.confidence_threshold == 0.8


# ── predict_single raises before model is loaded ──────────────────────────────

def test_predict_single_raises_when_model_not_loaded():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    with pytest.raises(RuntimeError, match="Model not loaded"):
        predictor.predict_single("some_image.jpg")


# ── predict_batch error handling ──────────────────────────────────────────────

def test_predict_batch_returns_error_entry_on_failure():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    results = predictor.predict_batch(["nonexistent.jpg"])
    assert len(results) == 1
    assert "error" in results[0]
    assert results[0]["image_path"] == "nonexistent.jpg"


def test_predict_batch_empty_list():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    results = predictor.predict_batch([])
    assert results == []


# ── get_prediction_statistics ─────────────────────────────────────────────────

def test_statistics_empty_predictions():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    stats = predictor.get_prediction_statistics([])
    assert stats["total_predictions"] == 0
    assert stats["average_confidence"] == 0
    assert stats["confidence_rate"] == 0


def test_statistics_all_confident():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
        confidence_threshold=0.5,
    )
    predictions = [
        {"predicted_species": "lion", "confidence": 0.9, "is_confident": True},
        {"predicted_species": "lion", "confidence": 0.8, "is_confident": True},
        {"predicted_species": "elephant", "confidence": 0.7, "is_confident": True},
    ]
    stats = predictor.get_prediction_statistics(predictions)
    assert stats["total_predictions"] == 3
    assert stats["confident_predictions"] == 3
    assert stats["confidence_rate"] == 1.0
    assert round(stats["average_confidence"], 2) == 0.8
    assert stats["species_distribution"]["lion"] == 2
    assert stats["species_distribution"]["elephant"] == 1


def test_statistics_mixed_confidence():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
        confidence_threshold=0.5,
    )
    predictions = [
        {"predicted_species": "lion", "confidence": 0.9, "is_confident": True},
        {"predicted_species": "zebra", "confidence": 0.3, "is_confident": False},
    ]
    stats = predictor.get_prediction_statistics(predictions)
    assert stats["total_predictions"] == 2
    assert stats["confident_predictions"] == 1
    assert stats["confidence_rate"] == 0.5


def test_statistics_ignores_error_entries():
    predictor = Predictor(
        model_path="models/test_model.pt",
        species_mapping=SPECIES_MAPPING,
    )
    predictions = [
        {"predicted_species": "lion", "confidence": 0.9, "is_confident": True},
        {"image_path": "bad.jpg", "error": "File not found"},
    ]
    stats = predictor.get_prediction_statistics(predictions)
    assert stats["total_predictions"] == 1
    assert stats["errors"] == 1
