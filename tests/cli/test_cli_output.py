"""Unit tests for the CLI output format module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from gitea.cli.output import OutputFormat, emit, get_output_format, print_envelope


class TestOutputFormat:
    """Tests for the OutputFormat enum."""

    def test_values(self) -> None:
        """Test that OutputFormat has the documented values."""
        assert OutputFormat.TEXT == "text"
        assert OutputFormat.JSON == "json"


class TestGetOutputFormat:
    """Tests for get_output_format."""

    def test_reads_format_from_context(self) -> None:
        """Should return the format stored by the root callback."""
        ctx = MagicMock()
        ctx.obj = {"output": OutputFormat.JSON}

        assert get_output_format(ctx) is OutputFormat.JSON

    def test_defaults_to_text_when_key_absent(self) -> None:
        """Should default to text when the context carries no format."""
        ctx = MagicMock()
        ctx.obj = {"config_path": None}

        assert get_output_format(ctx) is OutputFormat.TEXT

    def test_defaults_to_text_when_obj_missing(self) -> None:
        """Should default to text when the context has no object at all."""
        ctx = MagicMock()
        ctx.obj = None

        assert get_output_format(ctx) is OutputFormat.TEXT


class TestPrintEnvelope:
    """Tests for print_envelope."""

    def test_prints_data_and_metadata(self, capsys) -> None:
        """Should print the data/metadata envelope as JSON."""
        print_envelope(data=[{"id": 1}], metadata={"status_code": 200})

        out = json.loads(capsys.readouterr().out)
        assert out == {"data": [{"id": 1}], "metadata": {"status_code": 200}}

    def test_serializes_unknown_types_as_strings(self, capsys) -> None:
        """Should fall back to str() for values JSON cannot represent."""

        class Opaque:
            def __str__(self) -> str:
                return "opaque"

        print_envelope(data={"value": Opaque()}, metadata={})

        out = json.loads(capsys.readouterr().out)
        assert out["data"]["value"] == "opaque"


class TestEmit:
    """Tests for emit."""

    def test_json_format_prints_envelope(self, capsys) -> None:
        """Should print the envelope and skip the text renderer in JSON mode."""
        ctx = MagicMock()
        ctx.obj = {"output": OutputFormat.JSON}
        render_text = MagicMock()

        emit(ctx, data={"a": 1}, metadata={"b": 2}, render_text=render_text)

        render_text.assert_not_called()
        out = json.loads(capsys.readouterr().out)
        assert out == {"data": {"a": 1}, "metadata": {"b": 2}}

    def test_text_format_calls_renderer(self, capsys) -> None:
        """Should call the text renderer and print no envelope in text mode."""
        ctx = MagicMock()
        ctx.obj = {"output": OutputFormat.TEXT}
        render_text = MagicMock()

        emit(ctx, data={"a": 1}, metadata={"b": 2}, render_text=render_text)

        render_text.assert_called_once_with()
        assert capsys.readouterr().out == ""

    def test_text_format_without_renderer_prints_nothing(self, capsys) -> None:
        """Should print nothing in text mode when no renderer is supplied."""
        ctx = MagicMock()
        ctx.obj = {"output": OutputFormat.TEXT}

        emit(ctx, data={"a": 1}, metadata={"b": 2})

        assert capsys.readouterr().out == ""
