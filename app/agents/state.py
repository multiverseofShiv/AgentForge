from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    
    messages: Annotated[list[BaseMessage], add_messages]
    
    
    task: str
    
    #intermediate artifacts
    research_notes: str
    draft: str
    review_feedback: str
    sql_query: str
    sql_result: str
    
    
    final_output: str
    
    next_agent: str
    
    iteration_count: int
    
    human_approval_needed: bool
    
    status: str
    