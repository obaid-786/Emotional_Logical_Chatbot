from typing import List, Literal, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.schema import HumanMessage, AIMessage
from pydantic import BaseModel, Field
import requests
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()


class OllamaLLM:
    def invoke(self, messages):
        try:
            # Extract content from LangChain message objects
            if hasattr(messages[-1], 'content'):
                last_message = messages[-1].content
            else:
                last_message = messages[-1]["content"]

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gemma3:1b",
                    "prompt": last_message,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return AIMessage(content=result["response"])
            else:
                return AIMessage(content="Error: Ollama not responding properly")

        except Exception as e:
            return AIMessage(content=f"Error: {str(e)}")


llm = OllamaLLM()


class State(TypedDict):
    messages: Annotated[List, add_messages]
    message_type: str | None


graph_builder = StateGraph(State)


def classify_message(state: State):
    last_message = state["messages"][-1]

    # Simple classification logic
    emotional_keywords = ['feel', 'emotional', 'sad', 'happy', 'anxious', 'therapy', 'support', 'lonely', 'depressed']
    user_msg = last_message.content if hasattr(last_message, 'content') else last_message
    user_msg_lower = user_msg.lower()

    if any(keyword in user_msg_lower for keyword in emotional_keywords):
        return {"message_type": "emotional"}
    else:
        return {"message_type": "logical"}


def router(state: State):
    # This function should return the next node name, not update the state
    message_type = state.get("message_type", 'logical')
    if message_type == "emotional":
        return "therapist"
    return "logical"


def therapist_agent(state: State):
    last_message = state["messages"][-1]
    user_content = last_message.content if hasattr(last_message, 'content') else last_message

    prompt = f"""You are a compassionate therapist. Focus on the emotional aspect of the user's message.
Show empathy, validate their feelings, and help them process their emotions.
Ask thoughtful questions to help them explore their feelings more deeply.
Avoid giving logical solutions unless explicitly asked.

User message: {user_content}"""

    reply = llm.invoke([HumanMessage(content=prompt)])
    return {"messages": [reply]}


def logical_agent(state: State):
    last_message = state["messages"][-1]
    user_content = last_message.content if hasattr(last_message, 'content') else last_message

    prompt = f"""You are a purely logical assistant. Focus only on facts and information.
Provide clear, concise answers based on logic and evidence.
Do not address emotions or provide emotional support.
Be direct and straightforward in your responses.

User message: {user_content}"""

    reply = llm.invoke([HumanMessage(content=prompt)])
    return {"messages": [reply]}


# Build the graph correctly
graph_builder.add_node("classify_message", classify_message)
graph_builder.add_node("therapist", therapist_agent)
graph_builder.add_node("logical", logical_agent)

# Set the entry point
graph_builder.set_entry_point("classify_message")

# Add conditional routing directly from classify_message
graph_builder.add_conditional_edges(
    "classify_message",
    router,  # Use router function to determine next node
    {
        "therapist": "therapist",
        "logical": "logical"
    }
)

# Add edges from response nodes to end
graph_builder.add_edge("therapist", END)
graph_builder.add_edge("logical", END)

graph = graph_builder.compile()


# def run_chatbot():
#     state = {"messages": [], "message_type": None}
#
#     while True:
#         user_input = input("Message: ")
#         if user_input.lower() == "quit":
#             print("Goodbye!")
#             break
#
#         # Add user message
#         state["messages"] = state.get("messages", []) + [HumanMessage(content=user_input)]
#
#         # Invoke the graph
#         result_state = graph.invoke(state)
#
#         # Update state
#         state = result_state
#
#         # Print assistant response
#         if state.get("messages") and len(state["messages"]) > 0:
#             last_message = state["messages"][-1]
#             if hasattr(last_message, 'content'):
#                 print(f"Assistant: {last_message.content}")
#             else:
#                 print(f"Assistant: {last_message}")
#
#
# if __name__ == "__main__":
#     run_chatbot()