import unittest
from unittest.mock import patch
import app as flask_app


class TestElearningApp(unittest.TestCase):

    def setUp(self):
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def test_dashboard_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    @patch("app.run_query")
    def test_courses_endpoint(self, mock_run_query):
        mock_run_query.return_value = []
        response = self.client.get("/api/courses")
        self.assertEqual(response.status_code, 200)
        mock_run_query.assert_called_once()

    def test_unknown_page_returns_404(self):
        response = self.client.get("/page-that-does-not-exist")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
