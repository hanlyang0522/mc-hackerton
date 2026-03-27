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
    parser.add_argument(
        "--job",
        default="",
        help="지원 직무명 (Gemini 직무 관련 정보 추출에 사용)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = CoverLetterDataPipeline(db_root=Path(args.db_dir))
    output = pipeline.run(args.company, job_title=args.job)
    print(f"수집 완료: {output}")


if __name__ == "__main__":
    main()
