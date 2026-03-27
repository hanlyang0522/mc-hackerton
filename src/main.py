from __future__ import annotations

import argparse
from pathlib import Path

from .crawling.pipeline import CoverLetterDataPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="자소서 정보 수집 파이프라인")
    parser.add_argument("company", help="지원 기업명")
    parser.add_argument(
        "--db-dir",
        default="./db",
        help="JSON 저장 루트 디렉터리 (기본값: ./db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = CoverLetterDataPipeline(db_root=Path(args.db_dir))
    output = pipeline.run(args.company)
    print(f"수집 완료: {output}")


if __name__ == "__main__":
    main()
