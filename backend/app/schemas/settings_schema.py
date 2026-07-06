from typing import Dict

from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    valores: Dict[str, str]


class SettingsResponse(BaseModel):
    valores: Dict[str, str]
