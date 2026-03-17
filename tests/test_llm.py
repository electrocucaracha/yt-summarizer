import unittest

from yt_summarizer.llm import Client


class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.mock_model = "gpt-4"
        self.mock_api_base = "https://api.example.com"
        self.client = Client(model=self.mock_model, api_base=self.mock_api_base)

    def test_initialization(self):
        self.assertEqual(self.client.model, self.mock_model)
        self.assertEqual(self.client.api_base, self.mock_api_base)


if __name__ == "__main__":
    unittest.main()
