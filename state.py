from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass


class RestaurantState(TypedDict):
    # User input
    user_query: str

    # Order tracking
    order_items: List[Dict[str, Any]]

    # Tool results
    take_order_result: Optional[Dict[str, Any]]
    cook_result: Optional[Dict[str, Any]]
    serve_result: Optional[Dict[str, Any]]

    # Retry counters
    invalid_order_attempts: int
    take_order_retry_count: int
    cook_retry_count: int
    serve_retry_count: int

    # Flow control
    current_step: str
    should_end: bool
    end_reason: Optional[str]

    # LLM interaction
    llm_input_json: str
    llm_response: str

    # Menu reference
    menu: Dict[str, List[Dict[str, Any]]]

    # Flags for testing/simulation
    force_fail_take_order: bool
    force_fail_cook: bool
    force_fail_serve: bool


def create_initial_state(user_query: str, menu: Dict, **kwargs) -> RestaurantState:
    return RestaurantState(
        user_query=user_query,
        order_items=[],
        take_order_result=None,
        cook_result=None,
        serve_result=None,
        invalid_order_attempts=kwargs.get("invalid_order_attempts", 0),
        take_order_retry_count=kwargs.get("take_order_retry_count", 0),
        cook_retry_count=kwargs.get("cook_retry_count", 0),
        serve_retry_count=kwargs.get("serve_retry_count", 0),
        current_step="evaluate_query",
        should_end=False,
        end_reason=None,
        llm_input_json="",
        llm_response="",
        menu=menu,
        force_fail_take_order=kwargs.get("force_fail_take_order", False),
        force_fail_cook=kwargs.get("force_fail_cook", False),
        force_fail_serve=kwargs.get("force_fail_serve", False)
    )