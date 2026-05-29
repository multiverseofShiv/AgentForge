from __future__ import annotations

import os
import sys

from crewai import Agent, Crew, Process, Task


def _get_llm():
    groq_key = os.getenv("GROQ_API_KEY", "")
    
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
        return "groq/llama-3.1-70b-versatile"
    return "ollama/llama3"
    
    
def build_crew(task_description: str)-> Crew:
    
    llm = _get_llm()
    
    #Agents
    researcher = Agent(
        role = "Researcher",
        goal = (
            "Gather accurate, source-backed information about the task"
            "so the writer can produce a high-quality draft."),
        backstory=(
            "You are meticulous research analyst who cross checks facts"
            "acorss multiple sources. You cite every claim with a URL"
            "You stop researching once you hace enough material - you"
            "never pad your notes with irrelevent infomation"
        ),
        llm=llm,
        verbose=True,
        allow_delegation = False
    )
    
    writer = Agent(
        role = "writer",
        goal = (
            "Produce a clear, well-structured draft using ONLY the "
            "research notes provided. Never invent facts."
        ),
        backstory=(
            "You are skilled technical writer who turns raw research"
            "into polished prose. You preserve citation URLs from the "
            "notes and match the requeted format. If review feedback"
            "is provided, you address every point."
        ),
        llm=llm,
        verbose=True,
        allow_delegation = False
    )
    
    reviewer = Agent(
        role = "Reviewer",
        goal=(
            "Critique the draft against the research notes. Approve only "
            "when quality is high (score >= 8/10). Provide specific, "
            "actionable feedback."
        ),
        backstory=(
            "You are senior editor who checks for factual grounding "
            "task alignment, clarity, and proper citations. You reject "
            "drafts that contain fabricated claims or miss the point of "
            "the original task"
            ),
        llm=llm,
        verbose=True,
        allow_delegation = False
    )
    
    #tasks
    
    research_task = Task(
        description=(
            f"Research the following topic thoroughly:\n\n{task_description}\n\n"
            "Produce structured notes with: \n"
            "- SUMMARY (2-3 sentences)\n"
            "- KEY FACTS (bulleted, with source URLs)\n"
            "- OPEN QUESTIONS (if any)"
        ),
        expected_output=("Structured research notes with SUMMARY, KEY FACTS (cited), "
                         "and OPEN QUESTIONS sections"
                         ),
        agent=researcher,
        
    )
    
    writing_task = Task(
    description=(
        f"Research the following topic thoroughly:\n\n{task_description}\n\n"
        "Produce structured notes with: \n"
        "- SUMMARY (2-3 sentences)\n"
        "- KEY FACTS (bulleted, with source URLs)\n"
        "- OPEN QUESTIONS (if any)"
    ),
    expected_output=("Structured research notes with SUMMARY, KEY FACTS (cited), "
                        "and OPEN QUESTIONS sections"
                        ),
    agent=writer,
    context=[research_task]
    )
    
    writing_task = Task(
            description=(
                f"Using the research notes from the Researcher, write a polished draft for this task:\n\n{task_description}\n\n"
                "Rules: \n"
                "- Stay grounded in the research notes only\n"
                "- Preserve citation URLs\n"
                "- Default format: short report with Intro, Body, Conclusion"
            ),
            expected_output="A well-structured draft with inline citations.",
        agent=writer,
        context=[research_task]
        )
    
    
    review_task = Task(
            description=(
                "Review the Writer's draft against the original task and the Researcher's notes.\n\n"
                "Evaluate on:\n"
                "1. Factual grounding (every claim traces to research notes)\n"
                "2. Task alignment (answers what was asked)\n"
                "3. Clarity and structure\n"
                "4. Citations preserved\n\n"
                "Give a score (1-10) and specific feedback. If score >= 8, approve. "
                "Otherwise provide concrete fixes."
            ),
            expected_output=(
                "A review with: SCORE (1-10), DECISION (APPROVED/REVISE), and detailed FEEDBACK."
            ),
        agent=reviewer,
        context=[research_task, writing_task]
        )
    
    
    
    #crew
    crew = Crew(
        agents = [researcher, writer, reviewer],
        tasks = [research_task, writing_task, review_task],
        process=Process.sequential,
        verbose=True,
    )
    
    return crew


def run_crew(task_description: str) -> str:
    
    crew = build_crew(task_description)
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv()
    
    task = " ".join(sys.argv[1:]) if len(sys.argv)>1 else(
        "Research and write a short article about the transformer architecture"
        "in deep learning"
    )
    
    print(f"\n{"="*60}")
    print(f"TASK: {task}")
    print(f"{'='*60}\n")
    
    output = run_crew(task)
    
    print(f"\n{"="*60}")
    print("Final Output : ")
    print(f"{'='*60}")
    print(output)
    
    
    
    
    
    
    
    