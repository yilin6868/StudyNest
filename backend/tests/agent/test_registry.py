import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from pydantic import Field

from app.agent.context import CallSource, IntentEvidence, ToolExecutionContext, digest_arguments
from app.agent.contracts import ContractModel
from app.agent.permissions import PermissionLevel
from app.agent.registry import ToolDefinition, ToolRegistry


class EchoInput(ContractModel):
    value: int = Field(ge=0)


class EchoOutput(ContractModel):
    value: int


def _definition(**changes) -> ToolDefinition:
    values = {
        "name": "echo",
        "description": "返回数字",
        "input_model": EchoInput,
        "output_model": EchoOutput,
        "side_effect": False,
        "permission": PermissionLevel.AUTO,
        "timeout_seconds": 1,
        "handler": lambda raw, _context: EchoOutput(value=raw.value),
    }
    values.update(changes)
    return ToolDefinition(**values)


def _context(**changes) -> ToolExecutionContext:
    values = {
        "user_id": "user-1",
        "request_id": "request_123",
        "source": CallSource.AGENT,
        "db": Mock(),
    }
    values.update(changes)
    return ToolExecutionContext(**values)


def test_registry_rejects_duplicate_names_and_unsafe_confirmation_writes():
    registry = ToolRegistry()
    registry.register(_definition())
    with pytest.raises(ValueError):
        registry.register(_definition())
    with pytest.raises(ValueError):
        ToolRegistry().register(
            _definition(
                name="unsafe_confirm",
                side_effect=True,
                permission=PermissionLevel.CONFIRMATION_REQUIRED,
            )
        )


def test_registry_exposes_validated_tool_descriptions():
    registry = ToolRegistry()
    registry.register(_definition())

    description = registry.descriptions()[0]
    assert description["name"] == "echo"
    assert description["inputSchema"]["additionalProperties"] is False
    assert description["sideEffect"] is False


def test_unknown_and_invalid_arguments_never_run_a_handler():
    handler = Mock(return_value=EchoOutput(value=1))
    events = []
    registry = ToolRegistry(audit_sink=events.append)
    registry.register(_definition(handler=handler))

    unknown = registry.execute("run_shell", {}, _context())
    invalid = registry.execute("echo", {"value": -1}, _context())

    assert unknown.error.code == "TOOL_NOT_FOUND"
    assert invalid.error.code == "TOOL_INVALID_ARGUMENTS"
    handler.assert_not_called()
    assert all("secret" not in repr(event) for event in events)


def test_permission_is_checked_before_side_effect_handler():
    handler = Mock(return_value=EchoOutput(value=1))
    registry = ToolRegistry()
    registry.register(
        _definition(
            name="write_echo",
            side_effect=True,
            permission=PermissionLevel.EXPLICIT_INTENT,
            handler=handler,
        )
    )

    denied = registry.execute("write_echo", {"value": 1}, _context())

    assert denied.error.code == "TOOL_PERMISSION_DENIED"
    handler.assert_not_called()


def test_handler_and_result_failures_become_safe_errors():
    failing = ToolRegistry()
    failing.register(
        _definition(handler=lambda _raw, _context: (_ for _ in ()).throw(RuntimeError("database password")))
    )
    invalid_result = ToolRegistry()
    invalid_result.register(_definition(handler=lambda _raw, _context: {"value": "bad"}))

    failed = failing.execute("echo", {"value": 1}, _context())
    invalid = invalid_result.execute("echo", {"value": 1}, _context())

    assert failed.error.code == "TOOL_EXECUTION_FAILED"
    assert "password" not in failed.error.message
    assert invalid.error.code == "TOOL_INVALID_RESULT"


def test_timeout_rolls_back_and_is_not_retried():
    handler = Mock(
        side_effect=lambda raw, _context: (
            time.sleep(0.01),
            EchoOutput(value=raw.value),
        )[1]
    )
    db = Mock()
    registry = ToolRegistry()
    registry.register(_definition(timeout_seconds=0.001, handler=handler))

    result = registry.execute("echo", {"value": 1}, _context(db=db))

    assert result.error.code == "TOOL_TIMEOUT"
    assert handler.call_count == 1
    db.rollback.assert_called_once()


def test_side_effect_commits_once_per_request():
    handler = Mock(return_value=EchoOutput(value=1))
    db = Mock()
    context = _context(
        db=db,
        intent_evidence={
            "write_echo": IntentEvidence(
                user_id="user-1",
                request_id="request_123",
                tool_name="write_echo",
                arguments_digest=digest_arguments({"value": 1}),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
            )
        },
    )
    registry = ToolRegistry()
    registry.register(
        _definition(
            name="write_echo",
            side_effect=True,
            permission=PermissionLevel.EXPLICIT_INTENT,
            handler=handler,
        )
    )

    first = registry.execute("write_echo", {"value": 1}, context)
    second = registry.execute("write_echo", {"value": 1}, context)

    assert first.ok is True
    assert second.error.code == "TOOL_PERMISSION_DENIED"
    assert handler.call_count == 1
    db.commit.assert_called_once()
    assert context.tool_call_count == 2


def test_audit_sink_failure_does_not_break_tool_result():
    registry = ToolRegistry(
        audit_sink=lambda _event: (_ for _ in ()).throw(RuntimeError("audit down"))
    )
    registry.register(_definition())

    result = registry.execute("echo", {"value": 1}, _context())

    assert result.ok is True
