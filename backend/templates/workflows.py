"""
Pre-built workflow templates.
Each template provides nodes and edges compatible with the ReactFlow builder.
"""

TEMPLATES = [
    {
        "id": "research-summary",
        "name": "Research & Summarise",
        "description": "A researcher agent searches the web and passes findings to a writer agent that produces a polished summary.",
        "nodes": [
            {
                "id": "start-1",
                "type": "start",
                "position": {"x": 100, "y": 200},
                "data": {"label": "Start"},
            },
            {
                "id": "agent-researcher",
                "type": "agent",
                "position": {"x": 300, "y": 200},
                "data": {
                    "label": "Researcher",
                    "agent_id": "__RESEARCHER__",
                    "role": "researcher",
                    "system_prompt": "You are a thorough research assistant. Search the web to gather relevant, accurate information on the given topic. Summarise your findings clearly.",
                    "model": "gpt-4o-mini",
                    "tools": ["web_search", "get_current_datetime"],
                },
            },
            {
                "id": "agent-writer",
                "type": "agent",
                "position": {"x": 600, "y": 200},
                "data": {
                    "label": "Writer",
                    "agent_id": "__WRITER__",
                    "role": "writer",
                    "system_prompt": "You are a skilled content writer. Take the research findings provided to you and craft a clear, engaging, well-structured summary.",
                    "model": "gpt-4o-mini",
                    "tools": [],
                },
            },
            {
                "id": "end-1",
                "type": "end",
                "position": {"x": 900, "y": 200},
                "data": {"label": "End"},
            },
        ],
        "edges": [
            {"id": "e1", "source": "start-1", "target": "agent-researcher"},
            {"id": "e2", "source": "agent-researcher", "target": "agent-writer"},
            {"id": "e3", "source": "agent-writer", "target": "end-1"},
        ],
        "trigger": {"type": "manual"},
    },
    {
        "id": "customer-support",
        "name": "Customer Support Triage",
        "description": "A triage agent categorises the inbound query and routes it to a specialist support agent.",
        "nodes": [
            {
                "id": "start-1",
                "type": "start",
                "position": {"x": 100, "y": 200},
                "data": {"label": "Start"},
            },
            {
                "id": "agent-triage",
                "type": "agent",
                "position": {"x": 300, "y": 200},
                "data": {
                    "label": "Triage Agent",
                    "agent_id": "__TRIAGE__",
                    "role": "triage",
                    "system_prompt": "You are a customer support triage agent. Analyse the user query, classify it (billing / technical / general), and provide an initial helpful response before handing off context.",
                    "model": "gpt-4o-mini",
                    "tools": ["get_current_datetime"],
                },
            },
            {
                "id": "agent-specialist",
                "type": "agent",
                "position": {"x": 600, "y": 200},
                "data": {
                    "label": "Specialist Agent",
                    "agent_id": "__SPECIALIST__",
                    "role": "specialist",
                    "system_prompt": "You are a specialist support agent. Based on the triage context, provide a detailed, empathetic, and accurate resolution to the customer's issue.",
                    "model": "gpt-4o-mini",
                    "tools": ["web_search", "calculator"],
                },
            },
            {
                "id": "end-1",
                "type": "end",
                "position": {"x": 900, "y": 200},
                "data": {"label": "End"},
            },
        ],
        "edges": [
            {"id": "e1", "source": "start-1", "target": "agent-triage"},
            {"id": "e2", "source": "agent-triage", "target": "agent-specialist"},
            {"id": "e3", "source": "agent-specialist", "target": "end-1"},
        ],
        "trigger": {"type": "manual"},
    },
]
