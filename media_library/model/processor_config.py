from typing import List, Dict
from pydantic import BaseModel

class FieldRule(BaseModel):
    function: str
    params: List[str]

class ProcessorConfig(BaseModel):
    fields: Dict[str, FieldRule]