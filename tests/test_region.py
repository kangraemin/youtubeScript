import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker"))
from naver_search import _extract_region  # noqa: E402

CASES = [
    ("전남광주통합특별시 광산구 임방울대로 162", "광주"),
    ("전남광주 동구 금남로 1", "광주"),
    ("전남광주통합특별시 해남군 해남읍 1", "전남"),
    ("전남광주 여수시 중앙로 1", "전남"),
    ("광주광역시 서구 상무대로 1", "광주"),
    ("전라남도 영암군 영암읍 1", "전남"),
    ("전북특별자치도 전주시 완산구 경기전길 124", "전북"),
    ("경기도 과천시 별양상가2로 20 새서울쇼핑", "경기"),
    ("경기도 시흥시 서울대학로264번길 25", "경기"),
    ("경상남도 창원시 마산회원구 석전남9길 53-2", "경남"),
    ("전남광주통합특별시 담양군 대전면 병풍로 374", "전남"),
    ("서울특별시 강남구 테헤란로 1", "서울"),
    ("제주특별자치도 제주시 1", "제주"),
    ("강원특별자치도 강릉시 1", "강원"),
    ("세종특별자치시 한누리대로 1", "세종"),
    ("어딘가 123", None),
]


class ExtractRegionTest(unittest.TestCase):
    def test_cases(self):
        for address, region in CASES:
            with self.subTest(address=address):
                self.assertEqual(_extract_region(address), region)


if __name__ == "__main__":
    unittest.main()
