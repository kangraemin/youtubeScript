import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "scripts"),
                str(Path(__file__).resolve().parent.parent / "worker")]
import rematch_skipped as rm  # noqa: E402


class FakeDB:
    pass


class RematchTest(unittest.TestCase):
    def test_parse_json(self):
        self.assertEqual(rm.parse_json('앞말 {"items": [{"orig": "a"}]} 뒷말')["items"][0]["orig"], "a")
        self.assertIsNone(rm.parse_json("없음"))
        self.assertIsNone(rm.parse_json("{깨짐"))

    def test_in_sources(self):
        self.assertTrue(rm._in_sources("친정 엄마", "청주 친정엄마 식당"))
        self.assertFalse(rm._in_sources("우리집", "청주 친정엄마 식당"))
        self.assertFalse(rm._in_sources("가", "가나다"))

    def test_empty_candidate_not_searched(self):
        r = rm.match_one(None, {"video_id": "v"}, {}, "orig", {"name": ""}, "", True)
        self.assertEqual(r["result"], "no_candidate")

    def test_ungrounded_name_not_confident(self):
        import naver_search
        orig = naver_search.search_restaurant
        naver_search.search_restaurant = lambda n, h="": {"name": "완전다른집", "address": "충북 청주시 청원구",
                                                         "lat": 36.6, "lng": 127.4, "confidence": "high"}
        try:
            r = rm.match_one(None, {"video_id": "v"}, {}, "친정엄마", {"name": "완전다른집"}, "자막에 없음", True)
        finally:
            naver_search.search_restaurant = orig
        self.assertEqual(r["result"], "would_save")
        self.assertFalse(r["confident"])


if __name__ == "__main__":
    unittest.main()
