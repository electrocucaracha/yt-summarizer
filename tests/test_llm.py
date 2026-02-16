"""Tests for the LLM client module."""

from unittest.mock import Mock, patch

import pytest

from yt_summarizer.llm import Client


class TestLLMClient:
    """Test cases for LLM Client class."""

    def test_init(self):
        """Test LLM client initialization."""
        model = "ollama/llama3.2"
        api_base = "http://localhost:11434"

        client = Client(model=model, api_base=api_base)

        assert client.model == model
        assert client.api_base == api_base

    def test_init_custom_values(self):
        """Test LLM client initialization with custom values."""
        model = "gpt-4"
        api_base = "https://api.openai.com/v1"

        client = Client(model=model, api_base=api_base)

        assert client.model == model
        assert client.api_base == api_base

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_success(
        self, mock_completion, sample_transcript, sample_summary
    ):
        """Test successful text summarization."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = sample_summary
        mock_completion.return_value = mock_response

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        summary = client.summarize(sample_transcript)

        assert summary == sample_summary
        mock_completion.assert_called_once()

        # Verify the call was made with correct parameters
        call_args = mock_completion.call_args
        assert call_args.kwargs["model"] == "ollama/llama3.2"
        assert call_args.kwargs["api_base"] == "http://localhost:11434"
        assert call_args.kwargs["temperature"] == 0.1
        assert call_args.kwargs["stream"] is False

        # Verify messages were passed correctly
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert sample_transcript in messages[1]["content"]

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_api_error(self, mock_completion, sample_transcript):
        """Test summarization when API raises an exception."""
        mock_completion.side_effect = Exception("API Error")

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")

        with pytest.raises(Exception) as exc_info:
            client.summarize(sample_transcript)

        assert "API Error" in str(exc_info.value)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_get_main_points_success(
        self, mock_completion, sample_transcript, sample_main_points
    ):
        """Test successful main points extraction."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = sample_main_points
        mock_completion.return_value = mock_response

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        main_points = client.get_main_points(sample_transcript)

        assert main_points == sample_main_points
        mock_completion.assert_called_once()

        # Verify the call was made with correct parameters
        call_args = mock_completion.call_args
        assert call_args.kwargs["model"] == "ollama/llama3.2"
        assert call_args.kwargs["api_base"] == "http://localhost:11434"
        assert call_args.kwargs["temperature"] == 0.1
        assert call_args.kwargs["stream"] is False

        # Verify messages were passed correctly
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert sample_transcript in messages[1]["content"]

    @patch("yt_summarizer.llm.litellm.completion")
    def test_get_main_points_api_error(self, mock_completion, sample_transcript):
        """Test main points extraction when API raises an exception."""
        mock_completion.side_effect = Exception("API Error")

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")

        with pytest.raises(Exception) as exc_info:
            client.get_main_points(sample_transcript)

        assert "API Error" in str(exc_info.value)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_empty_text(self, mock_completion):
        """Test summarization with empty text."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "No content to summarize."
        mock_completion.return_value = mock_response

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        summary = client.summarize("")

        assert summary == "No content to summarize."
        mock_completion.assert_called_once()

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_long_text(self, mock_completion):
        """Test summarization with unusually long text."""
        long_text = "Word " * 10000  # Create long text
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summary of long text."
        mock_completion.return_value = mock_response

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        summary = client.summarize(long_text)

        assert summary == "Summary of long text."
        mock_completion.assert_called_once()

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_with_special_characters(self, mock_completion):
        """Test summarization with special characters in text."""
        special_text = "Text with special chars: @#$%^&*() and émojis 🎉"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summary with special characters."
        mock_completion.return_value = mock_response

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        summary = client.summarize(special_text)

        assert summary == "Summary with special characters."
        mock_completion.assert_called_once()

    @patch("yt_summarizer.llm.litellm.completion")
    def test_multiple_operations_same_client(
        self, mock_completion, sample_transcript, sample_summary, sample_main_points
    ):
        """Test that a single client can perform multiple operations."""
        # Setup mock to return different values
        mock_response_summary = Mock()
        mock_response_summary.choices = [Mock()]
        mock_response_summary.choices[0].message.content = sample_summary

        mock_response_points = Mock()
        mock_response_points.choices = [Mock()]
        mock_response_points.choices[0].message.content = sample_main_points

        mock_completion.side_effect = [mock_response_summary, mock_response_points]

        client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")

        summary = client.summarize(sample_transcript)
        main_points = client.get_main_points(sample_transcript)

        assert summary == sample_summary
        assert main_points == sample_main_points
        assert mock_completion.call_count == 2

    def test_different_models(self):
        """Test client initialization with different model identifiers."""
        test_cases = [
            ("ollama/llama3.2", "http://localhost:11434"),
            ("gpt-4", "https://api.openai.com/v1"),
            ("claude-3-opus", "https://api.anthropic.com"),
        ]

        for model, api_base in test_cases:
            client = Client(model=model, api_base=api_base)
            assert client.model == model
            assert client.api_base == api_base
