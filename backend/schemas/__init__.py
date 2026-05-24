from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    role: str = "assistant"
    system_prompt: str
    model: str = "gpt-4o-mini"
    tools: List[str] = []
    channels: List[str] = []
    memory_enabled: bool = True
    max_iterations: int = 10
    temperature: float = 0.7
    guardrails: Dict[str, Any] = {}
    skills: List[str] = []
    schedule: Dict[str, Any] = {}


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None
    max_iterations: Optional[int] = None
    temperature: Optional[float] = None
    guardrails: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    schedule: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    system_prompt: str
    model: str
    tools: List[str]
    channels: List[str]
    memory_enabled: bool
    max_iterations: int
    temperature: float
    guardrails: Dict[str, Any]
    skills: List[str]
    schedule: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    trigger: Dict[str, Any] = {"type": "manual"}


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    trigger: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    trigger: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExecutionCreate(BaseModel):
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    input_message: str = ""
    trigger_type: str = "manual"


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: Optional[str]
    agent_id: Optional[str]
    trigger_type: str
    input_message: str
    output_message: str
    status: str
    total_tokens: int
    total_cost: float
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExecutionLogResponse(BaseModel):
    id: str
    execution_id: str
    agent_id: Optional[str]
    agent_name: str
    log_type: str
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    agent_id: Optional[str]
    channel: str
    channel_user_id: str
    channel_chat_id: str
    direction: str
    content: str
    is_read: bool
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class RunAgentRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class RunWorkflowRequest(BaseModel):
    input_message: str
    trigger_type: str = "manual"
