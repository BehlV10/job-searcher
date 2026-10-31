import unittest
from scraper.parser import parse_salary, parse_yoe, parse_tech_stack, parse_seniority, generate_recruiter_links

class TestParser(unittest.TestCase):
    def test_parse_salary_range(self):
        text = "The base salary range for this role is $185,000 - $245,000 per year plus equity."
        sal = parse_salary(text)
        self.assertIsNotNone(sal)
        self.assertEqual(sal["min"], 185000)
        self.assertEqual(sal["max"], 245000)
        self.assertEqual(sal["period"], "yearly")

    def test_parse_salary_with_emdash(self):
        text = "Pay Range: $190,000 — $230,000 USD"
        sal = parse_salary(text)
        self.assertIsNotNone(sal)
        self.assertEqual(sal["min"], 190000)
        self.assertEqual(sal["max"], 230000)

    def test_parse_salary_k_format(self):
        text = "Expected compensation: $170k - $210k annually."
        sal = parse_salary(text)
        self.assertIsNotNone(sal)
        self.assertEqual(sal["min"], 170000)
        self.assertEqual(sal["max"], 210000)

    def test_parse_salary_hourly(self):
        text = "The hourly compensation is $90 - $115/hr based on experience."
        sal = parse_salary(text)
        self.assertIsNotNone(sal)
        self.assertEqual(sal["period"], "hourly")
        self.assertTrue(sal["min"] > 150000)

    def test_parse_yoe(self):
        text = "Qualifications: 7+ years of experience in distributed systems and cloud architecture."
        yoe = parse_yoe(text)
        self.assertIsNotNone(yoe)
        self.assertEqual(yoe["min_years"], 7)
        self.assertEqual(yoe["display"], "7+ years")

    def test_parse_yoe_range(self):
        text = "Requires 5-8 years of software engineering experience."
        yoe = parse_yoe(text)
        self.assertIsNotNone(yoe)
        self.assertEqual(yoe["min_years"], 5)
        self.assertEqual(yoe["max_years"], 8)
        self.assertEqual(yoe["display"], "5-8 years")

    def test_parse_tech_stack(self):
        text = "We are looking for someone with strong Python, Go, and Kubernetes skills working on AWS."
        stack = parse_tech_stack(text)
        self.assertIn("Python", stack)
        self.assertIn("Go", stack)
        self.assertIn("Kubernetes", stack)
        self.assertIn("AWS", stack)

    def test_recruiter_links(self):
        links = generate_recruiter_links("Datadog", "New York, NY", "Staff Software Engineer")
        self.assertIn("recruiter_search_url", links)
        self.assertIn("Datadog", links["recruiter_search_url"])
        self.assertIn("recruiter", links["recruiter_search_url"])

if __name__ == "__main__":
    unittest.main()
