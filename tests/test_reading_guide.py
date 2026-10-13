import json
import unittest
from pathlib import Path
from scripts.validate_reading_guide import validate_reading_guide

ROOT=Path(__file__).resolve().parents[1]
class ReadingGuideTest(unittest.TestCase):
    def setUp(self):
        self.guide=json.loads((ROOT/'web/content/reading-guides/WtEo31SpSeI.json').read_text())
        self.raw=(ROOT/'rawdata/transcripts/wepoll/WtEo31SpSeI.txt').read_text()
    def test_complete_guide(self):
        self.assertEqual(validate_reading_guide(self.guide,self.raw),[])
    def test_summary_cannot_replace_guide(self):
        self.assertTrue(validate_reading_guide(None,self.raw))
    def test_partial_read_rejected(self):
        self.guide['coverage']['read_lines']=200
        self.assertTrue(any('독해' in e for e in validate_reading_guide(self.guide,self.raw)))
    def test_empty_topic_rejected(self):
        self.guide['topics'][0]['points']=[]
        self.assertTrue(any('본문' in e for e in validate_reading_guide(self.guide,self.raw)))
    def test_original_required(self):
        self.assertTrue(validate_reading_guide(self.guide,None))
if __name__=='__main__':unittest.main()
