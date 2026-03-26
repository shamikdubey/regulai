"""
load_all_batches.py
Loads all batch_XX_*.json files from the data directory into the database.
Each batch file has the structure:
{
  "regulatory_bodies": [...],
  "licensing_pathways": [...],
  "allowable_limits": [...],
  "labeling_requirements": [...]
}

Run after migrations:
  docker-compose exec backend python -m scripts.load_all_batches
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal


DATA_DIR = Path(__file__).parent.parent / "data"


async def upsert_regulatory_bodies(session, items: list[dict]) -> int:
    from app.db.models import RegulatoryBody
    count = 0
    for item in items:
        result = await session.execute(
            text("SELECT id FROM regulatory_bodies WHERE acronym = :a AND jurisdiction = :j"),
            {"a": item["acronym"], "j": item["jurisdiction"]}
        )
        if not result.fetchone():
            session.add(RegulatoryBody(
                acronym=item["acronym"],
                name=item["name"],
                jurisdiction=item["jurisdiction"],
                domains=item.get("domains", []),
                established_year=item.get("established_year"),
                website=item.get("website"),
                description=item.get("description", ""),
                is_active=True,
            ))
            count += 1
    return count


async def upsert_licensing(session, items: list[dict]) -> int:
    from app.api.v1.endpoints.licensing import LicensingPathway
    count = 0
    for item in items:
        result = await session.execute(
            text("""SELECT id FROM licensing_pathways
                    WHERE jurisdiction = :j AND product_type = :p AND product_subtype = :s"""),
            {"j": item["jurisdiction"], "p": item["product_type"],
             "s": item.get("product_subtype")}
        )
        if not result.fetchone():
            session.add(LicensingPathway(**item))
            count += 1
    return count


async def upsert_limits(session, items: list[dict]) -> int:
    from app.api.v1.endpoints.allowable_limits import AllowableLimit
    count = 0
    for item in items:
        result = await session.execute(
            text("""SELECT id FROM allowable_limits
                    WHERE substance = :s AND jurisdiction = :j AND food_matrix = :f"""),
            {"s": item["substance"], "j": item["jurisdiction"], "f": item["food_matrix"]}
        )
        if not result.fetchone():
            session.add(AllowableLimit(**item))
            count += 1
    return count


async def upsert_labeling(session, items: list[dict]) -> int:
    from app.api.v1.endpoints.labeling import LabelingRequirement
    count = 0
    for item in items:
        result = await session.execute(
            text("""SELECT id FROM labeling_requirements
                    WHERE jurisdiction = :j AND product_type = :p"""),
            {"j": item["jurisdiction"], "p": item["product_type"]}
        )
        if not result.fetchone():
            session.add(LabelingRequirement(**item))
            count += 1
    return count


async def load_batch_file(session, path: Path) -> dict[str, int]:
    with open(path) as f:
        data = json.load(f)

    counts: dict[str, int] = {}

    if bodies := data.get("regulatory_bodies", []):
        counts["bodies"] = await upsert_regulatory_bodies(session, bodies)

    if pathways := data.get("licensing_pathways", []):
        counts["pathways"] = await upsert_licensing(session, pathways)

    if limits := data.get("allowable_limits", []):
        counts["limits"] = await upsert_limits(session, limits)

    if labeling := data.get("labeling_requirements", []):
        counts["labeling"] = await upsert_labeling(session, labeling)

    await session.commit()
    return counts


async def main():
    print("\n🌍 RegulAI v4 — Loading All Country Batch Data")
    print("=" * 50)

    # Find all batch files
    batch_files = sorted(DATA_DIR.glob("batch_*.json"))
    expanded_files = sorted(DATA_DIR.glob("*_expanded.json"))
    all_files = batch_files + expanded_files

    if not all_files:
        print("  No batch or expanded files found in", DATA_DIR)
        return

    total = {"bodies": 0, "pathways": 0, "limits": 0, "labeling": 0}

    async with AsyncSessionLocal() as session:
        for path in all_files:
            print(f"\n→ Loading {path.name}...")
            try:
                counts = await load_batch_file(session, path)
                for k, v in counts.items():
                    total[k] = total.get(k, 0) + v
                    if v > 0:
                        print(f"  ✓ {v} new {k}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                await session.rollback()

    print(f"\n✅ Complete. Totals added:")
    for k, v in total.items():
        print(f"  {k}: {v}")

    print("\nSummary by database table:")
    async with AsyncSessionLocal() as session:
        for table, label in [
            ("regulatory_bodies", "Regulatory bodies"),
            ("licensing_pathways", "Licensing pathways"),
            ("allowable_limits", "Allowable limits"),
            ("labeling_requirements", "Labeling profiles"),
            ("ingredient_specs", "Ingredient specs"),
        ]:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                n = result.scalar()
                print(f"  {label}: {n} total rows")
            except Exception as e:
                print(f"  {label}: error ({e})")


if __name__ == "__main__":
    asyncio.run(main())
