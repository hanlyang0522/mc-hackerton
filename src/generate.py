"""자소서 생성 CLI 진입점.

사용법:
  python -m src.generate "삼성전자" "SW개발" "지원 동기를 서술하시오" "어려운 문제 해결 경험을 기술하시오"
  python -m src.generate "삼성전자" "SW개발" "지원 동기를 서술하시오" --max-length 800
"""
from __future__ import annotations

import argparse
import json

from .pipeline import CoverLetterPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="자소서 자동 생성")
    parser.add_argument("company", help="지원 기업명")
    parser.add_argument("position", help="지원 직무명")
    parser.add_argument("questions", nargs="+", help="자소서 질문 (여러 개 가능)")
    parser.add_argument(
        "--max-length",
        type=int,
        default=500,
        help="질문당 글자수 제한 (기본값: 500, 공백 포함)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    max_lengths = [args.max_length] * len(args.questions)

    pipeline = CoverLetterPipeline()
    output = pipeline.run(
        company=args.company,
        position=args.position,
        questions=args.questions,
        max_lengths=max_lengths,
    )

    # 결과 출력
    for r in output.results:
        print(f"\n{'='*60}")
        print(f"질문: {r.question}")
        print(f"유형: {r.question_type or '공통'} | 소재: {r.material_display}")
        print(f"글자수: {r.char_count}자")
        print(f"{'-'*60}")
        print(r.draft)


if __name__ == "__main__":
    main()
