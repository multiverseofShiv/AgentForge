from typing import Literal, Optional
from pydantic import BaseModel, Field 


class SupervisorDecision(BaseModel):
    
    
    next_agent: Literal["researcher","writer","reviewer","sql_agent","FINISH"]
    reasoning: str= Field(description="Brief explanation for the routing decision")
    human_approval_needed: bool = Field(
        default= False,
        description="Set True when task requires human sign off before Proceeding"
    )
    
    
class ReviewDecision(BaseModel):
    
    approved: bool = Field(description="True if draft meets quality bar")
    feedback: str = Field(description="Specific, actionable feedback for the writer")
    score: int = Field(ge=1, le=10, description="Quality score 1-10")
    
    
# API SChemas
    
class TaskRequest(BaseModel):
    
    task:str = Field(
    min_length = 5,
    max_length = 2000,
    description = "Natural language task description for the agent pipeline",
    examples = ["Research and write a 500-word report on quantom computing trenda"]
    )
    context : Optional[str] = Field(
        default= None,
        description= "Optional additonal context or constraints for the agents."
        
    )
    
class TaskResoponse(BaseModel):
    
    task_id: str
    status : Literal["accepted","running","done","error"]
    message: Optional[str] = None
    result: Optional[str] = None