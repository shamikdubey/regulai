"""
seed_all.py — Seeds ALL regulatory data for RegulAI v4 (110 countries).
Run after: alembic upgrade head

Usage:
  docker-compose exec backend python -m scripts.seed_all
  # or directly:
  python -m scripts.seed_all
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal, engine, Base

DATA_DIR = Path(__file__).parent.parent / "data"


async def load_json(filename: str) -> list | dict:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  ⚠ {filename} not found — skipping")
        return []
    with open(path) as f:
        return json.load(f)


async def seed_countries(session):
    """Seed the countries reference table."""
    data = await load_json("countries.json")
    if not data:
        return 0

    count = 0
    await session.execute(text("DELETE FROM countries WHERE 1=1"))
    for region in data.get("regions", []):
        for country in region.get("countries", []):
            await session.execute(text("""
                INSERT INTO countries (value, label, flag, tier, region_id, region_label, region_color)
                VALUES (:value, :label, :flag, :tier, :region_id, :region_label, :region_color)
                ON CONFLICT (value) DO UPDATE SET
                    label = EXCLUDED.label,
                    flag = EXCLUDED.flag,
                    tier = EXCLUDED.tier,
                    region_id = EXCLUDED.region_id,
                    region_label = EXCLUDED.region_label,
                    region_color = EXCLUDED.region_color
            """), {
                "value": country["value"],
                "label": country["label"],
                "flag": country["flag"],
                "tier": country.get("tier", 2),
                "region_id": region["id"],
                "region_label": region["label"],
                "region_color": region["color"],
            })
            count += 1
    await session.commit()
    return count


async def seed_regulatory_bodies_expanded(session):
    """Seed expanded regulatory bodies from JSON."""
    from app.db.models import RegulatoryBody
    from sqlalchemy import delete

    data = await load_json("regulatory_bodies_expanded.json")
    if not data:
        return 0

    # Don't delete existing (preserve original 47 bodies)
    count = 0
    for item in data:
        # Check if already exists
        result = await session.execute(
            text("SELECT id FROM regulatory_bodies WHERE acronym = :acronym AND jurisdiction = :jur"),
            {"acronym": item["acronym"], "jur": item["jurisdiction"]}
        )
        existing = result.fetchone()
        if not existing:
            db_obj = RegulatoryBody(
                acronym=item["acronym"],
                name=item["name"],
                jurisdiction=item["jurisdiction"],
                domains=item.get("domains", []),
                established_year=item.get("established_year"),
                website=item.get("website"),
                description=item.get("description", ""),
                is_active=True,
            )
            session.add(db_obj)
            count += 1

    await session.commit()
    return count


async def seed_licensing_expanded(session):
    """Seed expanded licensing pathways from JSON."""
    from app.api.v1.endpoints.licensing import LicensingPathway

    data = await load_json("licensing_pathways_expanded.json")
    if not data:
        return 0

    count = 0
    for item in data:
        # Check if already exists
        result = await session.execute(
            text("""SELECT id FROM licensing_pathways
                    WHERE jurisdiction = :jur AND product_type = :pt AND product_subtype = :ps"""),
            {"jur": item["jurisdiction"], "pt": item["product_type"], "ps": item.get("product_subtype")}
        )
        existing = result.fetchone()
        if not existing:
            db_obj = LicensingPathway(**item)
            session.add(db_obj)
            count += 1

    await session.commit()
    return count


async def seed_allowable_limits_expanded(session):
    """Seed expanded allowable limits from JSON."""
    from app.api.v1.endpoints.allowable_limits import AllowableLimit

    data = await load_json("allowable_limits_expanded.json")
    if not data:
        return 0

    count = 0
    for item in data:
        # Check if already exists
        result = await session.execute(
            text("""SELECT id FROM allowable_limits
                    WHERE substance = :sub AND jurisdiction = :jur AND food_matrix = :fm"""),
            {"sub": item["substance"], "jur": item["jurisdiction"], "fm": item["food_matrix"]}
        )
        existing = result.fetchone()
        if not existing:
            db_obj = AllowableLimit(**item)
            session.add(db_obj)
            count += 1

    await session.commit()
    return count


async def seed_labeling_expanded(session):
    """Seed expanded labeling requirements from JSON."""
    from app.api.v1.endpoints.labeling import LabelingRequirement

    data = await load_json("labeling_requirements_expanded.json")
    if not data:
        return 0

    count = 0
    for item in data:
        result = await session.execute(
            text("""SELECT id FROM labeling_requirements
                    WHERE jurisdiction = :jur AND product_type = :pt"""),
            {"jur": item["jurisdiction"], "pt": item["product_type"]}
        )
        existing = result.fetchone()
        if not existing:
            db_obj = LabelingRequirement(**item)
            session.add(db_obj)
            count += 1

    await session.commit()
    return count


async def main():
    print("\n🌍 RegulAI v4 — Seeding 110-Country Regulatory Database")
    print("=" * 55)

    async with AsyncSessionLocal() as session:
        # 1. Countries reference table (creates 110-country map)
        print("\n→ Countries reference table...")
        # Countries table created by migration 0004
        try:
            n = await seed_countries(session)
            print(f"  ✓ {n} countries seeded")
        except Exception as e:
            print(f"  ⚠ Countries table may not exist yet — run migration first: {e}")

        # 2. Regulatory bodies (new countries)
        print("\n→ Regulatory bodies (new countries)...")
        try:
            n = await seed_regulatory_bodies_expanded(session)
            print(f"  ✓ {n} new regulatory bodies seeded")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # 3. Licensing pathways (new countries)
        print("\n→ Licensing pathways (new countries)...")
        try:
            n = await seed_licensing_expanded(session)
            print(f"  ✓ {n} new licensing pathways seeded")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # 4. Allowable limits (new countries)
        print("\n→ Allowable limits (new countries)...")
        try:
            n = await seed_allowable_limits_expanded(session)
            print(f"  ✓ {n} new allowable limits seeded")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # 5. Labeling requirements (new countries)
        print("\n→ Labeling requirements (new countries)...")
        try:
            n = await seed_labeling_expanded(session)
            print(f"  ✓ {n} new labeling profiles seeded")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("\n✅ Seeding complete.")
    print("\nNext step — seed via API (with auth token):")
    print("  POST /api/v1/ingredient-specs/seed")
    print("  POST /api/v1/allowable-limits/seed")
    print("  POST /api/v1/labeling-requirements/seed")
    print("  POST /api/v1/licensing-pathways/seed")
    print("  POST /api/v1/alerts/seed")
    print()


if __name__ == "__main__":
    asyncio.run(main())
