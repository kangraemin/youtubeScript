import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker"))
from address_key import address_key, same_place  # noqa: E402


class AddressKeyTest(unittest.TestCase):
    def test_province_spelling_variants_share_key(self):
        pairs = [
            ("서울특별시 서초구 사임당로 157 B1층 B102호", "서울 서초구 사임당로 157 B1층 B102호"),
            ("전남광주통합특별시 나주시 금남길 61", "전남광주 나주시 금남길 61"),
            ("전북특별자치도 전주시 덕진구 영동길 84", "전북 전주시 덕진구 영동길 84"),
            ("부산광역시 수영구 남천바다로 34-6 1층", "부산 수영구 남천바다로 34-6 1층"),
        ]
        for a, b in pairs:
            self.assertEqual(address_key(a), address_key(b), (a, b))

    def test_empty(self):
        self.assertIsNone(address_key(None))
        self.assertIsNone(address_key(""))

    def test_same_place(self):
        a = {"name": "사랑채", "address": "전남광주통합특별시 나주시 금남길 61", "lat": 35.0337109, "lng": 126.7142642}
        b = {"name": "사랑채", "address": "전남광주 나주시 금남길 61", "lat": 35.033711, "lng": 126.7142642}
        self.assertTrue(same_place(a, b))
        self.assertFalse(same_place(a, {**b, "name": "사랑방"}))
        self.assertFalse(same_place(a, {**b, "address": "전남광주 나주시 금남길 63"}))

    def test_same_rest_of_address_in_other_city_is_not_same(self):
        # 시·도만 다르고 나머지가 같은 주소(중구 …)는 좌표로 가른다
        seoul = {"name": "만두집", "address": "서울특별시 중구 중앙로 1", "lat": 37.56, "lng": 126.98}
        busan = {"name": "만두집", "address": "부산광역시 중구 중앙로 1", "lat": 35.10, "lng": 129.03}
        self.assertFalse(same_place(seoul, busan))

    def test_missing_coords_falls_back_to_address(self):
        a = {"name": "모즈", "address": "서울특별시 강남구 학동로55길 12-4 1층"}
        b = {"name": "모즈", "address": "서울 강남구 학동로55길 12-4 1층", "lat": 37.5, "lng": 127.0}
        self.assertTrue(same_place(a, b))


if __name__ == "__main__":
    unittest.main()
