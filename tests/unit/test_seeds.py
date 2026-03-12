from pathlib import Path

import yaml

from protocrawl.models import Protocol

SEEDS_DIR = Path(__file__).parent.parent.parent / "seeds" / "protocols"


class TestSeedProtocols:
    def test_all_seeds_validate(self):
        yaml_files = list(SEEDS_DIR.glob("*.yaml"))
        assert len(yaml_files) > 0, "No seed YAML files found"

        for f in yaml_files:
            data = yaml.safe_load(f.read_text())
            p = Protocol(**data)
            assert p.slug, f"{f.name} missing slug"
            assert p.name, f"{f.name} missing name"
            assert p.read_geometry.segments or p.read_geometry.read_type, (
                f"{f.name} missing read geometry"
            )

    def test_unique_slugs(self):
        slugs = []
        for f in SEEDS_DIR.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            slugs.append(data["slug"])
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_assay_family_coverage(self):
        """Ensure seeds cover multiple assay families."""
        families = set()
        for f in SEEDS_DIR.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            families.add(data["assay_family"])
        assert len(families) >= 4, (
            f"Expected at least 4 assay families, got {len(families)}: {families}"
        )

    def test_confidence_scores_in_range(self):
        for f in SEEDS_DIR.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            score = data["confidence_score"]
            assert 0.0 <= score <= 1.0, (
                f"{f.name} confidence_score {score} out of range"
            )
