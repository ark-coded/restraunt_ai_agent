import json
from typing import Dict, List, Any, Optional
from state import RestaurantState
import difflib
import re


def load_menu() -> Dict[str, List[Dict[str, Any]]]:
    """Load menu from JSON file"""
    with open("menu.json", "r") as f:
        return json.load(f)


def get_all_menu_items(menu: Dict) -> List[Dict[str, Any]]:
    """Flatten menu into a single list of items"""
    all_items = []
    for category, items in menu.items():
        all_items.extend(items)
    return all_items


def find_best_menu_match(query_word: str, menu_items: List[Dict[str, Any]], cutoff: float = 0.6) -> Optional[Dict[str, Any]]:
    """
    Small RAG / Fuzzy matching helper:
    Finds the best matching menu item for a misspelled or partial query term
    using difflib (SequenceMatcher).
    """
    best_match = None
    highest_score = 0.0

    query_word_lower = query_word.lower().strip()
    if len(query_word_lower) < 3:
        return None

    for item in menu_items:
        item_name = item["name"].lower()
        # Check similarity against full name or individual words in name
        score = difflib.SequenceMatcher(None, query_word_lower, item_name).ratio()

        # Also check against individual words in the menu item name
        item_words = item_name.split()
        for w in item_words:
            word_score = difflib.SequenceMatcher(None, query_word_lower, w).ratio()
            if word_score > score:
                score = word_score

        if score > highest_score:
            highest_score = score
            best_match = item

    if highest_score >= cutoff:
        return best_match
    return None


def parse_order_from_query(query: str, menu: Dict) -> List[Dict[str, Any]]:
    """
    Parse user query to extract order items with RAG / fuzzy spelling correction.
    Returns list of {item_id, quantity, item_name, price, stock}
    """
    order_items = []
    query_lower = query.lower()
    all_items = get_all_menu_items(menu)

    # First pass: check for exact substring matches
    matched_item_ids = set()
    for item in all_items:
        item_name_lower = item["name"].lower()
        if item_name_lower in query_lower:
            quantity = 1
            patterns = [
                rf'(\d+)\s*{re.escape(item_name_lower)}',
                rf'{re.escape(item_name_lower)}\s*(\d+)',
                rf'(one|two|three|four|five)\s*{re.escape(item_name_lower)}',
                rf'{re.escape(item_name_lower)}\s*(one|two|three|four|five)'
            ]
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    qty_str = match.group(1)
                    if qty_str.isdigit():
                        quantity = int(qty_str)
                    else:
                        word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
                        quantity = word_to_num.get(qty_str, 1)
                    break

            order_items.append({
                "item_id": item["id"],
                "item_name": item["name"],
                "quantity": quantity,
                "price": item["price"],
                "stock": item["stock"]
            })
            matched_item_ids.add(item["id"])

    # Second pass (Small RAG / Fuzzy Matching for spelling mistakes):
    # Tokenize query words and look for fuzzy matches against menu items
    words = re.findall(r'\b[a-zA-Z]{3,}\b', query_lower)
    skip_words = {"want", "order", "like", "please", "some", "give", "the", "and", "with", "would"}

    for word in words:
        if word in skip_words:
            continue

        # Check if this word or nearby chunk matches any menu item fuzzily
        best_item = find_best_menu_match(word, all_items, cutoff=0.65)
        if best_item and best_item["id"] not in matched_item_ids:
            # Try to find quantity preceding or following the word
            quantity = 1
            idx = query_lower.find(word)
            if idx != -1:
                # Check digits around the word
                context_window = query_lower[max(0, idx-15):min(len(query_lower), idx+len(word)+15)]
                qty_match = re.search(r'\b(\d+)\b', context_window)
                if qty_match:
                    quantity = int(qty_match.group(1))

            order_items.append({
                "item_id": best_item["id"],
                "item_name": best_item["name"],
                "quantity": quantity,
                "price": best_item["price"],
                "stock": best_item["stock"]
            })
            matched_item_ids.add(best_item["id"])

    return order_items


def take_order_tool(state: RestaurantState, force_fail: bool = False) -> Dict[str, Any]:
    """
    take_order tool: validates availability and deducts stock.
    """
    if force_fail:
        return {
            "success": False,
            "message": "Item out of stock or unavailable",
            "failed_items": state.get("order_items", [])
        }

    menu = state["menu"]
    order_items = state.get("order_items", [])

    if not order_items:
        return {
            "success": False,
            "message": "No valid menu items found in order",
            "failed_items": []
        }

    failed_items = []
    successful_items = []

    for item in order_items:
        item_id = item["item_id"]
        quantity = item["quantity"]

        menu_item = None
        for category, items in menu.items():
            for i in items:
                if i["id"] == item_id:
                    menu_item = i
                    break
            if menu_item:
                break

        if not menu_item or not menu_item.get("available", True):
            failed_items.append({
                "item_id": item_id,
                "reason": "Not available"
            })
        elif menu_item["stock"] < quantity:
            failed_items.append({
                "item_id": item_id,
                "reason": f"Insufficient stock. Available: {menu_item['stock']}"
            })
        else:
            # Deduct stock
            menu_item["stock"] -= quantity
            successful_items.append(item)

    if failed_items:
        return {
            "success": False,
            "message": "Some items could not be fulfilled due to stock/availability",
            "failed_items": failed_items
        }

    return {
        "success": True,
        "message": "Order taken successfully and stock updated",
        "successful_items": successful_items
    }


def cook_tool(state: RestaurantState, force_fail: bool = False) -> Dict[str, Any]:
    """
    cook tool: simulates kitchen preparation.
    """
    if force_fail:
        return {
            "success": False,
            "message": "Kitchen error: Unable to cook items right now."
        }

    order_items = state.get("order_items", [])
    if not order_items:
        return {
            "success": False,
            "message": "No items to cook."
        }

    return {
        "success": True,
        "message": "All items cooked successfully in the kitchen."
    }


def serve_tool(state: RestaurantState, force_fail: bool = False) -> Dict[str, Any]:
    """
    serve tool: simulates serving food to the customer table.
    """
    if force_fail:
        return {
            "success": False,
            "message": "Service error: Failed to serve the prepared food."
        }

    return {
        "success": True,
        "message": "Food served successfully to the customer."
    }
