"""Unit tests for configured result confidence validation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.config.settings import OpenAIConfig, ValidationConfig
from pg_mcp.services.result_validator import ResultValidator


class TestResultValidator:
    @pytest.mark.asyncio
    async def test_min_confidence_score_controls_acceptance(self) -> None:
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "confidence": 75,
                            "explanation": "Mostly matches",
                            "suggestion": None,
                        }
                    )
                )
            )
        ]
        openai_client = MagicMock()
        openai_client.chat.completions.create = AsyncMock(return_value=response)

        with patch(
            "pg_mcp.services.result_validator.AsyncOpenAI", return_value=openai_client
        ):
            validator = ResultValidator(
                openai_config=OpenAIConfig(api_key="sk-test"),
                validation_config=ValidationConfig(min_confidence_score=80),
            )
            result = await validator.validate(
                question="Count active users",
                sql="SELECT COUNT(*) FROM users",
                results=[{"count": 12}],
                row_count=1,
            )

        assert result.confidence == 75
        assert result.is_acceptable is False
