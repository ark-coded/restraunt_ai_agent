from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
import json

from state import RestaurantState, create_initial_state
from decision import decision_node, take_order_node, cook_node, serve_node
from tools import load_menu

# Load environment variables
load_dotenv()

# Load menu
MENU = load_menu()

SCHEMA_STR = '{"take_order": "true/false", "cook": "true/false", "serve": "true/false"}'

# Exact system prompt as given in prompt.txt
SYSTEM_PROMPT = f'''#ROLE
You are an AI agent for restaurant management system.
#TASK
Your job is to take query of the customer / langgraph inputs of negative cases, the langgraph inputs will be given to you in json format following this schema {SCHEMA_STR}.
#CONSTRAINTS
You can only answer to valid queries of the customer related to restaurant and the menu {json.dumps(MENU)}.
#OUTPUT FORMAT
For the inputs given to you, you will reply in human readable format always.
#EXAMPLES
langgraph input : {{"take_order" : "false"}} your response will be similar to:  "This item is not available for now for the quantity you've asked for. Please lower the quantity or order something else :)"
langgraph input : {{"cook" : "false"}} your response will be similar to : "Some error occured while cooking this please contact the staff."
#FALLBACK
User : ** Asks something that is not in menu ** your response will be similar to : "This item is not available in the menu. Please choose from the menu."
User : **Asks something unrelated to the restaurant** your response will be similar to : "This query is invalid, please write a valid query."
'''


def create_llm():
    """Create the Groq LLM instance"""
    return ChatGroq(
        model="qwen/qwen3.8-27b",
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY")
    )


def llm_node(state: RestaurantState) -> RestaurantState:
    """
    LLM node that formats the response using the system prompt.
    """
    llm = create_llm()

    # Pass langgraph input or query to LLM
    input_str = state.get("llm_input_json", "")
    if not input_str:
        input_str = state.get("user_query", "")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"langgraph input : {input_str}")
    ]

    response = llm.invoke(messages)
    state["llm_response"] = response.content
    return state


def route_decision(state: RestaurantState) -> str:
    """
    Router based on decision_node results.
    """
    step = state.get("current_step", "")
    if step == "end" or step == "invalid_query_reask":
        return "llm"
    elif step == "call_take_order":
        return "take_order"
    return "llm"


def route_take_order(state: RestaurantState) -> str:
    """
    Router based on take_order node results.
    """
    step = state.get("current_step", "")
    if step == "call_cook":
        return "cook"
    # take_order retry or failed -> goes to LLM
    return "llm"


def route_cook(state: RestaurantState) -> str:
    """
    Router based on cook node results.
    """
    step = state.get("current_step", "")
    if step == "call_serve":
        return "serve"
    # cook failed -> goes to LLM to inform user and re-ask
    return "llm"


def route_serve(state: RestaurantState) -> str:
    """
    Router based on serve node results.
    """
    step = state.get("current_step", "")
    if step == "call_cook":
        return "cook"
    # serve finished or failed -> goes to LLM
    return "llm"


def build_graph() -> StateGraph:
    """
    Build the LangGraph execution workflow.
    Flow:
    decision -> take_order -> cook -> serve -> llm -> END
               (on retry/failure branches -> llm / retry cook / END)
    """
    workflow = StateGraph(RestaurantState)

    # Add nodes
    workflow.add_node("decision", decision_node)
    workflow.add_node("take_order", take_order_node)
    workflow.add_node("cook", cook_node)
    workflow.add_node("serve", serve_node)
    workflow.add_node("llm", llm_node)

    # Entry point
    workflow.set_entry_point("decision")

    # Edges
    workflow.add_conditional_edges(
        "decision",
        route_decision,
        {
            "take_order": "take_order",
            "llm": "llm"
        }
    )

    workflow.add_conditional_edges(
        "take_order",
        route_take_order,
        {
            "cook": "cook",
            "llm": "llm"
        }
    )

    workflow.add_conditional_edges(
        "cook",
        route_cook,
        {
            "serve": "serve",
            "llm": "llm"
        }
    )

    workflow.add_conditional_edges(
        "serve",
        route_serve,
        {
            "cook": "cook",
            "llm": "llm"
        }
    )

    workflow.add_edge("llm", END)

    return workflow.compile()


class RestaurantAgent:
    """Main restaurant agent class"""

    def __init__(self):
        self.graph = build_graph()
        self.menu = MENU

    def process_query(self, user_query: str, **kwargs) -> Dict[str, Any]:
        """
        Process a user query through the LangGraph workflow.
        Returns dictionary containing llm_response and final_state.
        """
        initial_state = create_initial_state(user_query, self.menu, **kwargs)
        final_state = self.graph.invoke(initial_state)
        return {
            "response": final_state["llm_response"],
            "state": final_state
        }

    def get_menu_display(self) -> str:
        """Get formatted menu display"""
        lines = ["🍽️  **RESTAURANT MENU (VEGETARIAN)**  🍽️\n"]
        for category, items in self.menu.items():
            category_name = category.replace("_", " ").title()
            lines.append(f"\n**{category_name}:**")
            for item in items:
                status = f" (Stock: {item['stock']})" if item['stock'] < 10 else ""
                lines.append(f"  • {item['name']} - ₹{item['price']}{status}")
                lines.append(f"    {item['description']}")
        return "\n".join(lines)


def main():
    agent = RestaurantAgent()

    print(agent.get_menu_display())
    print("\n" + "=" * 60)
    print("Welcome to our Vegetarian Restaurant Management System! 🍽️")
    print("Type 'menu' to see menu, 'quit' to exit.")
    print("=" * 60 + "\n")

    invalid_attempts = 0

    while True:
        try:
            user_input = input("\n👤 You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n🤖 Agent: Thank you for visiting! Have a wonderful day! 👋")
                break

            if user_input.lower() == 'menu':
                print(agent.get_menu_display())
                continue

            if not user_input:
                continue

            result = agent.process_query(user_input, invalid_order_attempts=invalid_attempts)
            state = result["state"]

            print(f"\n🤖 Agent: {result['response']}")

            if state.get("should_end", False):
                print("\n[System: Graph execution completed / ended]")
                break
            else:
                invalid_attempts = state.get("invalid_order_attempts", 0)

        except KeyboardInterrupt:
            print("\n\n🤖 Agent: Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()