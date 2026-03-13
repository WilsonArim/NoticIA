"""Test publisher logic without network."""
import pytest
from openclaw.output.supabase_intake import SupabasePublisher, AREA_MAP
from openclaw.models import ClaimTriplet


def test_format_claims_with_triplets():
    claims = ["Russia imposed sanctions on EU"]
    triplets = [ClaimTriplet(
        claim="Russia imposed sanctions on EU",
        subject="Russia", action="imposed sanctions on", object="EU",
    )]
    result = SupabasePublisher._format_claims(claims, triplets)
    assert len(result) == 1
    assert result[0]["original_text"] == "Russia imposed sanctions on EU"
    assert result[0]["subject"] == "Russia"
    assert result[0]["predicate"] == "imposed sanctions on"
    assert result[0]["object"] == "EU"


def test_format_claims_without_triplets():
    claims = ["Some claim without triplet"]
    result = SupabasePublisher._format_claims(claims, [])
    assert len(result) == 1
    assert result[0]["original_text"] == "Some claim without triplet"
    assert "subject" not in result[0]


def test_format_claims_partial_match():
    claims = ["Claim A", "Claim B"]
    triplets = [ClaimTriplet(claim="Claim A", subject="A", action="does", object="B")]
    result = SupabasePublisher._format_claims(claims, triplets)
    assert result[0]["subject"] == "A"
    assert "subject" not in result[1]


def test_area_mapping_all_14():
    expected_areas = {
        "geopolitics": "Geopolitica", "defense": "Defesa", "economy": "Economia",
        "tech": "Tech", "energy": "Energia", "health": "Saude",
        "environment": "Ambiente", "crypto": "Crypto", "regulation": "Regulacao",
        "portugal": "Portugal", "science": "Ciencia", "financial_markets": "Mercados",
        "society": "Sociedade", "sports": "Desporto",
    }
    for key, expected_val in expected_areas.items():
        assert AREA_MAP[key] == expected_val, f"Mapping wrong for {key}"
    assert len(AREA_MAP) == 14


def test_stress_100_claims():
    claims = [f"Claim number {i}" for i in range(100)]
    triplets = [
        ClaimTriplet(claim=f"Claim number {i}", subject=f"S{i}", action="acts", object=f"O{i}")
        for i in range(100)
    ]
    result = SupabasePublisher._format_claims(claims, triplets)
    assert len(result) == 100
    assert all(r["original_text"].startswith("Claim number") for r in result)
    assert all("subject" in r for r in result)
