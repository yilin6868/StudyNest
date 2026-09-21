"""白名单用户偏好数据访问。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import UserPreference


class PreferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str, *, include_companion: bool = False) -> dict[str, object]:
        preference = self.db.scalar(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        if preference is None:
            result = {
                "buddy_gender": "male", "voice_enabled": False,
                "mid_session_encouragement_enabled": False,
                "proactive_reminder_enabled": False,
                "quiet_hours_start": None, "quiet_hours_end": None,
                "custom_focus_enabled": False, "default_focus_minutes": 25, "reminder_channel": "in_app",
            }
        else:
            result = {
            "buddy_gender": preference.buddy_gender,
            "voice_enabled": preference.voice_enabled,
            "mid_session_encouragement_enabled": preference.mid_session_encouragement_enabled,
            "proactive_reminder_enabled": preference.proactive_reminder_enabled,
            "quiet_hours_start": preference.quiet_hours_start,
            "quiet_hours_end": preference.quiet_hours_end,
            "custom_focus_enabled": preference.custom_focus_enabled,
            "default_focus_minutes": preference.default_focus_minutes,
            "reminder_channel": preference.reminder_channel,
            }
        if not include_companion:
            return {"buddy_gender": result["buddy_gender"], "voice_enabled": result["voice_enabled"]}
        return result

    def update(
        self,
        user_id: str,
        *,
        buddy_gender: str | None,
        voice_enabled: bool | None,
        mid_session_encouragement_enabled: bool | None = None,
        proactive_reminder_enabled: bool | None = None,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
        custom_focus_enabled: bool | None = None,
        default_focus_minutes: int | None = None,
        reminder_channel: str | None = None,
        now: datetime,
        include_companion: bool = False,
    ) -> dict[str, object]:
        preference = self.db.scalar(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        if preference is None:
            preference = UserPreference(
                user_id=user_id,
                buddy_gender=buddy_gender or "male",
                voice_enabled=voice_enabled if voice_enabled is not None else False,
                mid_session_encouragement_enabled=mid_session_encouragement_enabled or False,
                proactive_reminder_enabled=proactive_reminder_enabled or False,
                quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                custom_focus_enabled=custom_focus_enabled or False,
                default_focus_minutes=default_focus_minutes or 25,
                reminder_channel=reminder_channel or "in_app",
                created_at=now,
                updated_at=now,
            )
            self.db.add(preference)
        else:
            if buddy_gender is not None:
                preference.buddy_gender = buddy_gender
            if voice_enabled is not None:
                preference.voice_enabled = voice_enabled
            if mid_session_encouragement_enabled is not None:
                preference.mid_session_encouragement_enabled = mid_session_encouragement_enabled
            if proactive_reminder_enabled is not None:
                preference.proactive_reminder_enabled = proactive_reminder_enabled
            if quiet_hours_start is not None:
                preference.quiet_hours_start = quiet_hours_start
            if quiet_hours_end is not None:
                preference.quiet_hours_end = quiet_hours_end
            if custom_focus_enabled is not None:
                preference.custom_focus_enabled = custom_focus_enabled
            if default_focus_minutes is not None:
                preference.default_focus_minutes = default_focus_minutes
            if reminder_channel is not None:
                preference.reminder_channel = reminder_channel
            preference.updated_at = now
        result = {
            "buddy_gender": preference.buddy_gender,
            "voice_enabled": preference.voice_enabled,
            "mid_session_encouragement_enabled": preference.mid_session_encouragement_enabled,
            "proactive_reminder_enabled": preference.proactive_reminder_enabled,
            "quiet_hours_start": preference.quiet_hours_start,
            "quiet_hours_end": preference.quiet_hours_end,
            "custom_focus_enabled": preference.custom_focus_enabled,
            "default_focus_minutes": preference.default_focus_minutes,
            "reminder_channel": preference.reminder_channel,
        }
        if not include_companion:
            return {"buddy_gender": result["buddy_gender"], "voice_enabled": result["voice_enabled"]}
        return result
