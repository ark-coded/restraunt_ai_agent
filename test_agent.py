"""
Comprehensive test script for the Restaurant Agent LangGraph workflow.
Includes testing for RAG spelling tolerance.
"""
from agent import RestaurantAgent


def test_successful_flow():
    print("=" * 60)
    print("TEST 1: Successful Order Flow (take_order -> cook -> serve)")
    print("=" * 60)
    agent = RestaurantAgent()
    query = "I would like to order Crispy Paneer Tikka and Butter Naan"
    print(f"User Query: '{query}'")
    result = agent.process_query(query)
    print(f"LLM Response:\n{result['response']}\n")
    print(f"Final State Step: {result['state']['current_step']}")
    print(f"Should End: {result['state']['should_end']}")


def test_spelling_tolerance_rag():
    print("=" * 60)
    print("TEST 1.1: RAG Spelling Tolerance (Misspelled order items)")
    print("=" * 60)
    agent = RestaurantAgent()
    # "Crispy Paner Tika" (Paneer misspelled) and "Buter Nan" (Butter Naan misspelled)
    query = "I want to order Crispy Paner Tika and Buter Nan"
    print(f"User Query (with typos): '{query}'")
    result = agent.process_query(query)
    print(f"Extracted Order Items: {result['state'].get('order_items')}")
    print(f"LLM Response:\n{result['response']}\n")


def test_invalid_query_flow():
    print("=" * 60)
    print("TEST 2: Invalid Query / Unrelated to restaurant (3 strikes -> END)")
    print("=" * 60)
    agent = RestaurantAgent()
    query = "What is quantum physics?"
    print(f"User Query: '{query}'")

    # Attempt 1
    res1 = agent.process_query(query, invalid_order_attempts=0)
    print(f"Attempt 1 Response: {res1['response']}")

    # Attempt 2
    res2 = agent.process_query(query, invalid_order_attempts=1)
    print(f"Attempt 2 Response: {res2['response']}")

    # Attempt 3 (3rd strike -> should end)
    res3 = agent.process_query(query, invalid_order_attempts=2)
    print(f"Attempt 3 Response: {res3['response']}")
    print(f"Should End: {res3['state']['should_end']}")


def test_take_order_failure():
    print("=" * 60)
    print("TEST 3: take_order tool failure / out of stock (3 retries -> END)")
    print("=" * 60)
    agent = RestaurantAgent()
    query = "I want Crispy Paneer Tikka"
    print(f"User Query: '{query}'")
    res = agent.process_query(query, force_fail_take_order=True, take_order_retry_count=2)
    print(f"LLM Response:\n{res['response']}")
    print(f"Should End: {res['state']['should_end']}")


def test_cook_failure():
    print("=" * 60)
    print("TEST 4: cook tool failure (LLM informs inconvenience in kitchen)")
    print("=" * 60)
    agent = RestaurantAgent()
    query = "I want Vegetable Biryani"
    print(f"User Query: '{query}'")
    res = agent.process_query(query, force_fail_cook=True)
    print(f"LLM Response:\n{res['response']}")
    print(f"Current Step: {res['state']['current_step']}")


def test_serve_failure():
    print("=" * 60)
    print("TEST 5: serve tool failure on 3rd retry (Apologize & END)")
    print("=" * 60)
    agent = RestaurantAgent()
    query = "I want Dal Makhani and Tandoori Roti"
    print(f"User Query: '{query}'")
    res = agent.process_query(query, force_fail_serve=True, serve_retry_count=2)
    print(f"LLM Response:\n{res['response']}")
    print(f"Should End: {res['state']['should_end']}")


if __name__ == "__main__":
    test_successful_flow()
    print("\n")
    test_spelling_tolerance_rag()
    print("\n")
    test_invalid_query_flow()
    print("\n")
    test_take_order_failure()
    print("\n")
    test_cook_failure()
    print("\n")
    test_serve_failure()
