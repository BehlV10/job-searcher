import unittest
from scraper.parser import (
    parse_salary,
    parse_yoe,
    parse_tech_stack,
    parse_seniority,
    parse_discipline
)

class TestParser(unittest.TestCase):
    def test_parse_seniority_levels(self):
        self.assertEqual(parse_seniority("Senior Staff Software Engineer, Backend"), "Senior Staff")
        self.assertEqual(parse_seniority("Sr. Staff Distributed Systems Engineer"), "Senior Staff")
        self.assertEqual(parse_seniority("Principal Software Engineer - Cloud Platform"), "Principal")
        self.assertEqual(parse_seniority("Distinguished Engineer"), "Principal")
        self.assertEqual(parse_seniority("Staff Software Engineer, Data Infrastructure"), "Staff")
        self.assertEqual(parse_seniority("Senior Backend Engineer"), "Senior")
        self.assertEqual(parse_seniority("Engineering Manager, Core Systems"), "Engineering Manager")

    def test_parse_discipline(self):
        self.assertEqual(parse_discipline("Staff Machine Learning Engineer"), "Machine Learning / AI")
        self.assertEqual(parse_discipline("Senior AI Engineer - Generative AI"), "Machine Learning / AI")
        self.assertEqual(parse_discipline("Senior Applied Scientist - AI Platform"), "Machine Learning / AI")
        self.assertEqual(parse_discipline("Staff Software Engineer, Distributed Systems"), "General Software")
        self.assertEqual(parse_discipline("Senior Backend Engineer, Payments"), "General Software")

    def test_parse_salary(self):
        text = "Base salary is $195,000 - $265,000 per year."
        sal = parse_salary(text)
        self.assertIsNotNone(sal)
        self.assertEqual(sal["min"], 195000)
        self.assertEqual(sal["max"], 265000)

if __name__ == "__main__":
    unittest.main()
