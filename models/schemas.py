
from pydantic import BaseModel, Field
from typing import Any

# Clase para representar un objeto global en el contexto 
class GlobalObjectForContext(BaseModel):
    id_global: str
    etiqueta: str
    confianza: float = Field(ge=0.0, le=1.0)
    contexto: str | None = None
    question: str | None = None
    sensores: dict[str, Any] = Field(default_factory=dict)
    cameras_seen: list[str] = Field(default_factory=list)
    camera_id: str | None = None
    bbox: tuple[int, int, int, int] | None = None
    image_base64: str | None = None

