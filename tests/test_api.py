import unittest

from fastapi.testclient import TestClient

from main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "hello"})

    def test_payments(self):
        response = self.client.get("/payments")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "payment api"})

    def test_batch(self):
        response = self.client.get("/batch")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "batch api"})

    def test_metrics(self):
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("# HELP", response.text)
        self.assertIn("# TYPE", response.text)


if __name__ == "__main__":
    unittest.main()