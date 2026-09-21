"""搭子形象和语音偏好工具。"""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, model_validator

from ...repositories.preferences import PreferenceRepository
from ..context import ToolExecutionContext
from ..contracts import ContractModel, PreferenceState
from ..permissions import PermissionLevel
from ..registry import ToolDefinition


class UpdatePreferenceInput(ContractModel):
    buddy_gender: Literal["male", "female"] | None = None
    voice_enabled: bool | None = None

    @model_validator(mode="after")
    def contains_a_change(self) -> "UpdatePreferenceInput":
        if self.buddy_gender is None and self.voice_enabled is None:
            raise ValueError("至少提供一个需要修改的偏好")
        return self


def update_preference(
    raw: BaseModel, context: ToolExecutionContext
) -> PreferenceState:
    args = UpdatePreferenceInput.model_validate(raw)
    now = datetime.now(ZoneInfo(context.timezone_name))
    result = PreferenceRepository(context.db).update(
        context.user_id,
        buddy_gender=args.buddy_gender,
        voice_enabled=args.voice_enabled,
        now=now,
    )
    return PreferenceState(
        buddy_gender=result["buddy_gender"],
        voice_enabled=result["voice_enabled"],
    )


PREFERENCE_TOOLS = (
    ToolDefinition(
        name="update_preference",
        description="在用户明确要求时修改搭子形象或语音偏好",
        input_model=UpdatePreferenceInput,
        output_model=PreferenceState,
        side_effect=True,
        permission=PermissionLevel.EXPLICIT_INTENT,
        timeout_seconds=2,
        handler=update_preference,
    ),
)
