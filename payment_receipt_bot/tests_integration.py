"""Integration test: full flow from data generation to compressed image."""
import asyncio
import sys
import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from payment_receipt_bot.engines.data_generator import IndianDataGenerator
from payment_receipt_bot.engines.snapshot_engine import SnapshotEngine
from payment_receipt_bot.utils.image_processor import compress_image
from payment_receipt_bot.modifiers import MODIFIERS


async def main():
    templates_dir = ROOT / "payment_receipt_bot" / "html_templates"
    out_dir = ROOT / "snapshots" / "integration"
    out_dir.mkdir(parents=True, exist_ok=True)

    gen = IndianDataGenerator(realism_level=3)
    engine = SnapshotEngine(output_dir=str(out_dir))

    config = {
        "receiver_mode": "random",
        "payer_mode": "random",
        "amount_min": 1000,
        "amount_max": 50000,
        "amount_rounding": "thousands",
        "utr_mode": "random",
        "datetime_mode": "random",
    }

    await engine.initialize()
    try:
        results = []
        for html_file in sorted(templates_dir.glob("*.html")):
            stem = html_file.stem.lower()
            modifier = None
            for key, cls in MODIFIERS.items():
                if key in stem:
                    modifier = cls
                    break
            if modifier is None:
                modifier = MODIFIERS["gpay"]

            data = gen.generate_complete_transaction(config, app=modifier.app_name)
            m = modifier(html_file)
            rendered = m.modify(data)

            tmp = out_dir / f"tmp_{html_file.stem}.html"
            tmp.write_text(rendered, encoding="utf-8")
            shot = await engine.capture(tmp, f"flow_{html_file.stem}")
            tmp.unlink(missing_ok=True)

            compressed = compress_image(shot, quality=85)
            ok = shot.exists() and shot.stat().st_size > 0
            ok_c = compressed.exists() and compressed.stat().st_size < 10 * 1024 * 1024
            print(f"{'OK ' if ok and ok_c else 'FAIL'} {html_file.name}: "
                  f"shot={shot.stat().st_size if shot.exists() else 0}B, "
                  f"compressed={compressed.stat().st_size if compressed.exists() else 0}B")
            results.append(ok and ok_c)
            compressed.unlink(missing_ok=True)
            shot.unlink(missing_ok=True)
    finally:
        await engine.close()

    success = all(results)
    print(f"\n=== Integration: {sum(results)}/{len(results)} passed ===")
    sys.exit(0 if success else 1)


asyncio.run(main())
