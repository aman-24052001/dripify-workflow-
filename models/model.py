import uuid
from typing import Optional, Union, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date


class WorkflowChatMessage(BaseModel):
    question: str
    response: Optional[str] = None

class WorkflowChat(BaseModel) :
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    workflowid: str
    messages: List[WorkflowChatMessage]

    class Config:
        json_schema_extra = {
            "example": {
                "_id": "123654789",
                "workflowid": "7896541230",
                "messages": [
                    {
                        "question": "What is your name?",
                        "response": "John Doe"
                    }
                ]
            }
        }