from typing import Dict, Any
from state import RestaurantState
import json


def is_valid_restaurant_query(query: str, menu: Dict) -> bool:
    """
    Check if query is valid for restaurant/menu.
    """
    query_lower = query.lower().strip()
    if not query_lower:
        return False

    restaurant_keywords = [
        "order", "menu", "food", "eat", "hungry", "dish", "item",
        "price", "cost", "available", "veg", "vegetarian", "dinner",
        "lunch", "breakfast", "meal", "appetizer", "main", "dessert",
        "drink", "beverage", "bread", "naan", "roti", "rice", "dal",
        "paneer", "vegetable", "biryani", "curry", "gravy", "sauce",
        "spring roll", "tikka", "lassi", "chai", "jamun", "kulfi", "soda"
    ]

    all_items = []
    for category, items in menu.items():
        for item in items:
            all_items.append(item["name"].lower())

    has_restaurant_keyword = any(kw in query_lower for kw in restaurant_keywords)
    has_menu_item = any(item in query_lower for item in all_items)
    is_greeting = any(g in query_lower for g in ["hello", "hi", "hey", "good morning", "good evening", "menu"])

    return has_restaurant_keyword or has_menu_item or is_greeting


def decision_node(state: RestaurantState) -> RestaurantState:
    """
    Decision function node: evaluates input query or current status and decides next tool/action.
    """
    current_step = state["current_step"]

    # Step 1: Initial query evaluation or re-evaluation
    if current_step == "evaluate_query":
        query = state["user_query"]
        menu = state["menu"]

        # Check if valid query and if any order item matches
        from tools import parse_order_from_query
        order_items = parse_order_from_query(query, menu)

        if not is_valid_restaurant_query(query, menu) or not order_items:
            state["invalid_order_attempts"] += 1
            if state["invalid_order_attempts"] >= 3:
                state["should_end"] = True
                state["current_step"] = "end"
                state["llm_input_json"] = json.dumps({"query": "invalid"})
            else:
                state["current_step"] = "invalid_query_reask"
                state["llm_input_json"] = json.dumps({"query": "invalid"})
        else:
            state["order_items"] = order_items
            state["invalid_order_attempts"] = 0
            state["current_step"] = "call_take_order"

    return state


def take_order_node(state: RestaurantState) -> RestaurantState:
    """
    Node for take_order tool execution & decision logic.
    """
    from tools import take_order_tool
    force_fail = state.get("force_fail_take_order", False)
    result = take_order_tool(state, force_fail=force_fail)
    state["take_order_result"] = result

    if not result["success"]:
        state["take_order_retry_count"] += 1
        if state["take_order_retry_count"] >= 3:
            state["should_end"] = True
            state["current_step"] = "end"
            state["llm_input_json"] = json.dumps({"take_order": "false"})
        else:
            state["current_step"] = "take_order_retry"
            state["llm_input_json"] = json.dumps({"take_order": "false"})
    else:
        state["take_order_retry_count"] = 0
        state["current_step"] = "call_cook"
        state["llm_input_json"] = json.dumps({"take_order": "true"})

    return state


def cook_node(state: RestaurantState) -> RestaurantState:
    """
    Node for cook tool execution & decision logic.
    """
    from tools import cook_tool
    force_fail = state.get("force_fail_cook", False)
    result = cook_tool(state, force_fail=force_fail)
    state["cook_result"] = result

    if not result["success"]:
        state["cook_retry_count"] += 1
        # Cook tool failed -> LLM will inform user inconvenience happened in kitchen and ask to re-order
        state["current_step"] = "cook_failed_reask"
        state["llm_input_json"] = json.dumps({"cook": "false"})
    else:
        state["cook_retry_count"] = 0
        state["current_step"] = "call_serve"
        state["llm_input_json"] = json.dumps({"cook": "true"})

    return state


def serve_node(state: RestaurantState) -> RestaurantState:
    """
    Node for serve tool execution & decision logic.
    """
    from tools import serve_tool
    force_fail = state.get("force_fail_serve", False)
    result = serve_tool(state, force_fail=force_fail)
    state["serve_result"] = result

    if not result["success"]:
        state["serve_retry_count"] += 1
        if state["serve_retry_count"] >= 3:
            state["should_end"] = True
            state["current_step"] = "end"
            state["llm_input_json"] = json.dumps({"serve": "false"})
        else:
            # Retry calling cook
            state["current_step"] = "call_cook"
    else:
        state["should_end"] = True
        state["current_step"] = "end"
        state["llm_input_json"] = json.dumps({"serve": "true"})

    return state