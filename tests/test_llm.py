"""Tests for the LLM client module."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import litellm
import pytest

from yt_summarizer.llm import (
    EXECUTIVE_SUMMARY_CHAR_LIMIT,
    MAIN_POINTS_CHAR_LIMIT,
    TRANSCRIPT_SUMMARY_CHAR_LIMIT,
    Client,
    LLMConnectionError,
    LLMContextWindowError,
)


class TestLLMClient(unittest.TestCase):
    """Tests for the LLM Client class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = "gpt-4"
        self.mock_api_base = "https://api.example.com"
        self.client = Client(model=self.mock_model, api_base=self.mock_api_base)
        compressor = patch("yt_summarizer.llm.headroom_compress", None)
        compressor.start()
        self.addCleanup(compressor.stop)

    def test_initialization(self):
        """Test that the LLM client initializes with the correct attributes."""
        self.assertEqual(self.client.model, self.mock_model)
        self.assertEqual(self.client.api_base, self.mock_api_base)

    @patch("yt_summarizer.llm.headroom_compress")
    @patch("yt_summarizer.llm.get_prompt_token_limit", return_value=15_360)
    def test_completion_compresses_messages_with_model_budget(
        self, mock_token_limit, mock_compress
    ):
        """Completion prompts are compressed within the model's safe input budget."""
        compressed_messages = [{"role": "user", "content": "compressed"}]
        mock_compress.return_value = SimpleNamespace(
            messages=compressed_messages,
            tokens_before=1_000,
            tokens_after=500,
            transforms_applied=["test"],
        )
        with patch("yt_summarizer.llm.litellm.completion") as mock_completion:
            mock_completion.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="ok"))]
            )

            self.client.summarize("Transcript text")

        mock_token_limit.assert_called_once_with(self.mock_model)
        mock_compress.assert_called_once()
        compression_kwargs = mock_compress.call_args.kwargs
        self.assertIn("Transcript text", compression_kwargs["messages"][1]["content"])
        self.assertEqual(compression_kwargs["model"], self.mock_model)
        self.assertEqual(compression_kwargs["model_limit"], 15_360)
        self.assertTrue(compression_kwargs["compress_user_messages"])
        self.assertEqual(compression_kwargs["protect_recent"], 0)
        self.assertEqual(
            mock_completion.call_args.kwargs["messages"], compressed_messages
        )

    @patch("yt_summarizer.llm.headroom_compress", side_effect=RuntimeError("failed"))
    @patch("yt_summarizer.llm.get_prompt_token_limit", return_value=10_000)
    def test_completion_falls_back_to_original_messages_when_compression_fails(
        self, _mock_token_limit, _mock_compress
    ):
        """A compressor failure must not prevent the LLM request."""
        with patch("yt_summarizer.llm.litellm.completion") as mock_completion:
            mock_completion.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="ok"))]
            )

            self.client.summarize("Transcript text")

        self.assertIn(
            "Transcript text",
            mock_completion.call_args.kwargs["messages"][1]["content"],
        )

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_wraps_api_connection_errors(self, mock_completion):
        """Connection failures should become actionable LLM connection errors."""
        mock_completion.side_effect = litellm.exceptions.APIConnectionError(
            message="connection refused",
            llm_provider="ollama",
            model=self.mock_model,
        )

        with self.assertRaises(LLMConnectionError) as exc_info:
            self.client.summarize("Transcript text")

        self.assertIn("LLM endpoint", str(exc_info.exception))
        self.assertIn(self.mock_api_base, str(exc_info.exception))
        self.assertIn(self.mock_model, str(exc_info.exception))

    @patch("yt_summarizer.llm.litellm.completion")
    def test_get_main_points_returns_response_content(self, mock_completion):
        """Successful completions should return the message content."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="- point 1\n- point 2"))]
        )

        self.assertEqual(
            self.client.get_main_points("Transcript text"),
            "- point 1\n- point 2",
        )

    @patch("yt_summarizer.llm.litellm.completion")
    def test_generate_executive_summary_uses_dedicated_prompt(self, mock_completion):
        """Executive summaries should use a synthesis-focused prompt."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Executive summary text"))]
        )

        result = self.client.generate_executive_summary("Summary A\n\nSummary B")

        self.assertEqual(result, "Executive summary text")
        messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("executive briefing assistant", messages[0]["content"])
        self.assertIn("Create an executive summary", messages[1]["content"])
        self.assertIn("Summary A", messages[1]["content"])
        self.assertIn("Summary B", messages[1]["content"])
        self.assertIn(str(EXECUTIVE_SUMMARY_CHAR_LIMIT), messages[0]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_generate_executive_summary_includes_playlist_title_context(
        self, mock_completion
    ):
        """Executive summaries should include playlist title context when provided."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Executive summary text"))]
        )

        self.client.generate_executive_summary(
            "Summary A\n\nSummary B", playlist_title="Engineering Weekly"
        )

        messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(
            "The playlist title is: Engineering Weekly.", messages[1]["content"]
        )

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_includes_transcript_text(self, mock_completion):
        """Summaries should be generated from the supplied transcript text."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        self.client.summarize("Transcript text")

        summary_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("Transcript text", summary_messages[1]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_completion_omits_api_base_when_not_configured(self, mock_completion):
        """Provider-native models should not be forced onto a custom base URL."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )
        client = Client(model="github_copilot/gpt-4", api_base=None)

        client.summarize("Transcript text")

        self.assertNotIn("api_base", mock_completion.call_args.kwargs)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_summarize_and_main_points_prompts_use_updated_limits(
        self, mock_completion
    ):
        """Transcript prompts should advertise the configured character limits."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        self.client.summarize("Transcript text")
        summary_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(
            str(TRANSCRIPT_SUMMARY_CHAR_LIMIT), summary_messages[0]["content"]
        )
        self.assertIn(
            str(TRANSCRIPT_SUMMARY_CHAR_LIMIT), summary_messages[1]["content"]
        )

        self.client.get_main_points("Transcript text")
        main_points_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn(str(MAIN_POINTS_CHAR_LIMIT), main_points_messages[0]["content"])
        self.assertIn(str(MAIN_POINTS_CHAR_LIMIT), main_points_messages[1]["content"])


class TestSummarizationChain(unittest.TestCase):
    """Tests for context-based reduction instead of provider-specific heuristics."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client(model="ollama/llama3.2", api_base="http://localhost:11434")
        self.long_text = "word " * 20_000
        compressor = patch("yt_summarizer.llm.headroom_compress", None)
        compressor.start()
        self.addCleanup(compressor.stop)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_short_text_skips_the_chain(self, mock_completion):
        """Text that fits the context window should use a single request."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary"))]
        )

        self.client.summarize("Short transcript")

        self.assertEqual(mock_completion.call_count, 1)

    @patch("yt_summarizer.llm.litellm.completion")
    def test_long_text_is_chunked_and_reduced(self, mock_completion):
        """Long text should be summarized per chunk before the final prompt."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Partial summary"))]
        )

        self.client.summarize(self.long_text)

        self.assertGreater(mock_completion.call_count, 1)
        chunk_messages = mock_completion.call_args_list[0].kwargs["messages"]
        self.assertIn("part 1 of", chunk_messages[1]["content"])
        self.assertLess(len(chunk_messages[1]["content"]), len(self.long_text))

        final_messages = mock_completion.call_args.kwargs["messages"]
        self.assertIn("Partial summary", final_messages[1]["content"])

    @patch("yt_summarizer.llm.litellm.completion")
    def test_chain_stops_when_text_does_not_shrink(self, mock_completion):
        """Non-shrinking chunk summaries must not loop indefinitely."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=self.long_text))]
        )

        with self.assertRaises(LLMContextWindowError):
            self.client.summarize(self.long_text)

        self.assertTrue(
            all(
                "part " in call.kwargs["messages"][1]["content"]
                for call in mock_completion.call_args_list
            )
        )


class TestDirectCompletionBehavior(unittest.TestCase):
    """Prompts that fit the model should get one direct completion."""

    @patch("yt_summarizer.llm.headroom_compress", None)
    @patch("yt_summarizer.llm.litellm.completion")
    def test_non_ollama_model_sends_full_text(self, mock_completion):
        """Hosted models with large contexts should receive the untouched text."""
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary"))]
        )
        client = Client(model="gpt-4", api_base=None)
        long_text = "word " * 2000

        client.summarize(long_text)

        self.assertEqual(mock_completion.call_count, 1)
        self.assertIn(
            long_text, mock_completion.call_args.kwargs["messages"][1]["content"]
        )


@pytest.fixture
def budgeted_completion(monkeypatch):
    """Provide deterministic token counts and reject every oversized API call."""
    from yt_summarizer import llm

    def token_count(*, model, messages):
        return sum(len(message["content"].encode("utf-8")) + 16 for message in messages)

    monkeypatch.setattr(llm, "headroom_compress", None)
    monkeypatch.setattr(llm, "get_prompt_token_limit", lambda _model: 1200)
    monkeypatch.setattr(llm.litellm, "token_counter", token_count)
    calls = []

    def complete(**kwargs):
        assert token_count(model=kwargs["model"], messages=kwargs["messages"]) <= 1200
        assert kwargs["max_tokens"] == 1024
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="Partial summary"))
            ]
        )

    monkeypatch.setattr(llm.litellm, "completion", complete)
    return calls


def _first_pass_excerpts(calls):
    """Extract only the first map pass when several reduction passes were needed."""
    first_prompt = calls[0]["messages"][1]["content"]
    total = int(first_prompt.split(" of ", 2)[1])
    return [
        call["messages"][1]["content"].split("\n\n", 1)[1] for call in calls[:total]
    ]


@pytest.mark.parametrize("model", ["ollama/llama3.2", "gpt-4", "custom/model"])
@pytest.mark.parametrize(
    "method", ["summarize", "get_main_points", "generate_executive_summary"]
)
def test_long_inputs_fit_every_request(budgeted_completion, model, method):
    """All analysis paths reduce oversized prompts, regardless of provider."""
    client = Client(model=model, api_base="http://localhost:11434")
    text = "first detail " + "word " * 2000 + "last detail"

    assert getattr(client, method)(text) == "Partial summary"

    assert len(budgeted_completion) > 1
    excerpts = _first_pass_excerpts(budgeted_completion)
    assert " ".join(excerpts).split() == text.split()
    final = budgeted_completion[-1]
    assert "Partial summary" in final["messages"][1]["content"]
    assert final["api_base"] == "http://localhost:11434"
    if method == "get_main_points":
        assert "bullet points" in final["messages"][1]["content"]


@pytest.mark.parametrize("text", ["Short transcript", ""])
def test_small_inputs_skip_the_chain(budgeted_completion, text):
    """Fitting prompts retain their content and use one request."""
    Client(model="custom/model", api_base=None).summarize(text)

    assert len(budgeted_completion) == 1
    assert budgeted_completion[0]["messages"][1]["content"].endswith(text)


@pytest.mark.parametrize("extra_tokens", [0, 1])
def test_complete_prompt_budget_boundary(budgeted_completion, extra_tokens):
    """Exactly fitting prompts are sent directly; one token over is reduced."""
    client = Client(model="custom/model", api_base=None)
    client.summarize("")
    empty_prompt = budgeted_completion.pop()["messages"]
    overhead = sum(
        len(message["content"].encode("utf-8")) + 16 for message in empty_prompt
    )
    text = "x" * (1200 - overhead + extra_tokens)

    client.summarize(text)

    assert (len(budgeted_completion) == 1) == (extra_tokens == 0)


@pytest.mark.parametrize(
    "text",
    ["\u5bc6\u96c6\u7684\u5b57\u5e55" * 1000, "x" * 10_000],
    ids=["multibyte", "unbroken"],
)
def test_chunks_handle_multibyte_and_unbroken_text(budgeted_completion, text):
    """Token-aware splitting handles Unicode and text without word boundaries."""
    Client(model="custom/model", api_base=None).summarize(text)

    excerpts = _first_pass_excerpts(budgeted_completion)
    assert "".join(excerpts) == text


def test_compression_can_avoid_the_chain(budgeted_completion, monkeypatch):
    """A prompt that fits after compression needs no map-reduce requests."""
    from yt_summarizer import llm

    monkeypatch.setattr(
        llm,
        "headroom_compress",
        lambda **_kwargs: SimpleNamespace(
            messages=[{"role": "user", "content": "Compressed transcript"}],
            tokens_before=10_000,
            tokens_after=50,
            transforms_applied=["test"],
        ),
    )

    Client(model="custom/model", api_base=None).summarize("word " * 2000)

    assert len(budgeted_completion) == 1


@pytest.mark.parametrize("compression_fails", [False, True])
def test_insufficient_compression_uses_chain(
    budgeted_completion, monkeypatch, compression_fails
):
    """Compression failures and misleading metrics cannot bypass the token guard."""
    from yt_summarizer import llm

    def compress(**kwargs):
        if compression_fails:
            raise RuntimeError("compression unavailable")
        return SimpleNamespace(
            messages=kwargs["messages"],
            tokens_before=10_000,
            tokens_after=1,
            transforms_applied=[],
        )

    monkeypatch.setattr(llm, "headroom_compress", compress)

    Client(model="custom/model", api_base=None).summarize("word " * 2000)

    assert len(budgeted_completion) > 1


def test_pass_limit_fails_without_final_request(budgeted_completion, monkeypatch):
    """Progress that still exceeds the budget at the pass limit is not sent."""
    from yt_summarizer import llm

    monkeypatch.setattr(llm, "MAX_CHAIN_PASSES", 1)
    monkeypatch.setattr(
        Client, "_condense", lambda _self, text, _limit: text[: len(text) // 2]
    )
    with pytest.raises(LLMContextWindowError, match="pass limit"):
        Client(model="custom/model", api_base=None).summarize("word " * 2000)

    assert not budgeted_completion


def test_oversized_instructions_fail_before_api_call(budgeted_completion):
    """Playlist context is counted together with the source and system prompt."""
    with pytest.raises(LLMContextWindowError, match="instructions"):
        Client(model="custom/model", api_base=None).generate_executive_summary(
            "Summary", playlist_title="x" * 2000
        )

    assert not budgeted_completion


def test_unknown_tokenizer_still_reduces_input(budgeted_completion, monkeypatch):
    """Tokenizer errors use conservative sizing for both map and final requests."""
    from yt_summarizer import llm

    def fail(**_kwargs):
        raise ValueError("unsupported tokenizer")

    monkeypatch.setattr(llm.litellm, "token_counter", fail)

    Client(model="custom/model", api_base=None).summarize("word " * 2000)

    assert len(budgeted_completion) > 1


@pytest.mark.parametrize("content", [None, "", "   "])
def test_empty_chunk_responses_fail_explicitly(
    budgeted_completion, monkeypatch, content
):
    """A missing chunk summary cannot silently discard part of the source."""
    from yt_summarizer import llm

    monkeypatch.setattr(
        llm.litellm,
        "completion",
        lambda **_kwargs: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        ),
    )

    with pytest.raises(ValueError, match="returned no text"):
        Client(model="custom/model", api_base=None).summarize("word " * 2000)


if __name__ == "__main__":
    unittest.main()
