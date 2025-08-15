import streamlit as st
import os
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import TypedDict, Optional

# Load environment variables
load_dotenv()

# Streamlit app setup
st.set_page_config(page_title="AI Meeting Agent 📝", layout="wide")
st.title("AI Meeting Preparation Agent 📝")

# Get API keys from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Check if API keys are available
if not groq_api_key:
    st.error("GROQ_API_KEY not found in .env file. Please add it to your .env file.")
    st.stop()

if not tavily_api_key:
    st.error("TAVILY_API_KEY not found in .env file. Please add it to your .env file.")
    st.stop()

# Set environment variables
os.environ["GROQ_API_KEY"] = groq_api_key
os.environ["TAVILY_API_KEY"] = tavily_api_key

# Groq LLM
llm = ChatGroq(
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
    temperature=0.3,
    timeout=60
)

# Tavily search tool
tavily_tool = TavilySearchResults()

# Define a state schema TypedDict for LangGraph
class MeetingState(TypedDict, total=False):
    company_name: str
    meeting_objective: str
    attendees: str
    meeting_duration: int
    focus_areas: str
    context_analysis: Optional[str]
    industry_insights: Optional[str]
    strategy: Optional[str]
    executive_brief: Optional[str]

# Streamlit Inputs
company_name = st.text_input("Enter the company name:")
meeting_objective = st.text_input("Enter the meeting objective:")
attendees = st.text_area("Enter the attendees and their roles (one per line):")
meeting_duration = st.number_input("Enter the meeting duration (in minutes):", min_value=15, max_value=180, value=60, step=15)
focus_areas = st.text_input("Enter any specific areas of focus or concerns:")

user_inputs: MeetingState = {
    "company_name": company_name,
    "meeting_objective": meeting_objective,
    "attendees": attendees,
    "meeting_duration": meeting_duration,
    "focus_areas": focus_areas,
}

#########################
# Agent Functions (Nodes)
#########################

def context_analyzer(state):
    query = f"{state['company_name']} company recent news and updates"
    search_results = tavily_tool.invoke({"query": query})
    docs = "\n".join([result["content"] for result in search_results])

    prompt = ChatPromptTemplate.from_template("""
    You are a Meeting Context Specialist.
    Analyze the context for a meeting with {company_name}.
    Meeting Objective: {meeting_objective}
    Attendees: {attendees}
    Duration: {meeting_duration}
    Focus Areas: {focus_areas}

    Use the following recent search results:\n{docs}

    Summarize:
    - Recent news and press releases
    - Key products or services
    - Major competitors

    Provide a markdown summary with headings.
    """)
    chain = prompt | llm
    output = chain.invoke({**state, "docs": docs})
    return {"context_analysis": output.content}

def industry_insights(state):
    prompt = ChatPromptTemplate.from_template("""
    You are an Industry Expert.
    Based on the following context: {context_analysis}
    
    Analyze the industry around {company_name}.
    Include:
    - Industry trends
    - Competitive landscape
    - Opportunities and threats
    - Market positioning

    Provide markdown output with headings.
    """)
    chain = prompt | llm
    output = chain.invoke(state)
    return {"industry_insights": output.content}

def strategy_formulation(state):
    prompt = ChatPromptTemplate.from_template("""
    You are a Meeting Strategist.
    Based on:
    - Context: {context_analysis}
    - Industry: {industry_insights}
    
    Develop a {meeting_duration}-minute meeting agenda:
    - Time-boxed items
    - Key talking points
    - Speakers
    - Discussion prompts
    - Strategies for focus areas: {focus_areas}

    Output markdown with headings.
    """)
    chain = prompt | llm
    output = chain.invoke(state)
    return {"strategy": output.content}

def executive_brief(state):
    prompt = ChatPromptTemplate.from_template("""
    You are a Communication Specialist.
    Create an executive brief based on the following:

    - Meeting Objective: {meeting_objective}
    - Attendees: {attendees}
    - Context: {context_analysis}
    - Industry: {industry_insights}
    - Strategy: {strategy}

    Include:
    1. One-page executive summary
    2. Key talking points with data/examples
    3. Anticipated questions and answers
    4. Strategic recommendations and next steps

    Format using markdown with H1, H2, H3 headings.
    """)
    chain = prompt | llm
    output = chain.invoke(state)
    return {"executive_brief": output.content}

#####################
# LangGraph Workflow
#####################

workflow = StateGraph(MeetingState)

workflow.add_node("ContextAnalyzer", context_analyzer)
workflow.add_node("IndustryInsights", industry_insights)
workflow.add_node("StrategyFormulation", strategy_formulation)
workflow.add_node("ExecutiveBrief", executive_brief)

workflow.set_entry_point("ContextAnalyzer")
workflow.add_edge("ContextAnalyzer", "IndustryInsights")
workflow.add_edge("IndustryInsights", "StrategyFormulation")
workflow.add_edge("StrategyFormulation", "ExecutiveBrief")
workflow.add_edge("ExecutiveBrief", END)

graph = workflow.compile()

if st.button("Prepare Meeting"):
    with st.spinner("Running agents..."):
        final_state = graph.invoke(user_inputs)
    st.markdown(final_state["executive_brief"])

st.sidebar.markdown("""
## How to use this app:
1. Make sure your GROQ_API_KEY or any LLM API KEY and TAVILY_API_KEY are set in the .env file.
2. Fill out meeting details.
3. Click 'Prepare Meeting'.
4. Wait for your executive brief.
""")
