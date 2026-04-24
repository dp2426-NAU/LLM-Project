"""
Seeds the vector store with sample regulations and policies from data/.
Run this once after setting up your environment.

Usage:
    python scripts/seed_sample_data.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    from app.config import get_settings
    from store.vector_store import VectorStore
    from store.version_tracker import VersionTracker
    from ingestion.pipeline import IngestionPipeline

    settings = get_settings()
    vs = VectorStore(settings)
    vt = VersionTracker(settings.version_db_path)
    vt.init_db()
    pipeline = IngestionPipeline(settings, vs, vt)

    data_dir = Path(__file__).parent.parent / "data"

    # Ingest regulations
    reg_dir = data_dir / "sample_regulations"
    for reg_file in sorted(reg_dir.glob("*.txt")):
        parts = reg_file.stem.split("_")
        version_tag = parts[-1] if parts else "v1"
        regulation_id = "_".join(parts[:-1]) or reg_file.stem

        logger.info("Ingesting regulation: %s", reg_file.name)
        try:
            pipeline.ingest_regulation(
                regulation_id=regulation_id,
                body="SEC",
                title=regulation_id.replace("_", " ").title(),
                version_tag=version_tag,
                file_path=str(reg_file),
            )
        except Exception as e:
            logger.error("Failed to ingest %s: %s", reg_file.name, e)

    # Ingest policies
    policy_dir = data_dir / "sample_policies"
    policy_meta = {
        "pol_records_management": ("POL-REC-001", "Electronic Records Management", "Compliance & Operations"),
        "pol_aml_kyc": ("POL-AML-001", "AML and KYC Procedures", "Financial Crime"),
        "pol_risk_capital": ("POL-RISK-002", "Capital Adequacy and Stress Testing", "Risk Management"),
    }

    for pol_file in sorted(policy_dir.glob("*.txt")):
        stem = pol_file.stem
        policy_id, title, department = policy_meta.get(stem, (stem.upper(), stem.replace("_", " ").title(), "Compliance"))

        logger.info("Ingesting policy: %s", pol_file.name)
        try:
            pipeline.ingest_policy(
                policy_id=policy_id,
                title=title,
                department=department,
                file_path=str(pol_file),
            )
        except Exception as e:
            logger.error("Failed to ingest %s: %s", pol_file.name, e)

    stats = vs.collection_stats()
    logger.info("Seeding complete. Stats: %s", stats)


if __name__ == "__main__":
    main()
