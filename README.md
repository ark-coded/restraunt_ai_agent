# Vegetarian Restaurant AI Management Agent (LangGraph + LangChain + Groq)

An AI agent built with **LangGraph**, **LangChain**, and **Groq (Qwen/Llama)** for managing a vegetarian restaurant system.

## 🌟 Features & Decision Graph Rules

The agent follows a deterministic decision flow:
1. **Query & Order Validation**:
   - If a valid order is received, the decision function calls the `take_order` tool.
   - If an invalid query/order occurs **3 times**, the LangGraph ends.
2. **Order Placement (`take_order` tool)**:
   - Validates menu items, availability, and stock.
   - If `take_order` fails (e.g. out of stock), it retries up to **3 times** before ending the graph.
   - On success, it calls the `cook` tool.
3. **Kitchen Cooking (`cook` tool)**:
   - If the `cook` tool fails, the LLM informs the customer that an inconvenience happened in the kitchen and re-asks to order.
   - On success, it calls the `serve` tool.
4. **Food Service (`serve` tool)**:
   - If `serve` fails, it retries the `cook` tool up to **3 times**.
   - If `serve` fails on the 3rd attempt, the graph ends after informing the user and apologizing for the inconvenience.
   - If `serve` succeeds, the graph ends and the LLM asks if the customer wants to order something else.

---

## 📁 Project Structure

```
restaurant/
├── .env                 # Environment variables (GROQ_API_KEY)
├── menu.json            # Vegetarian menu (Appetizers, Main Course, Breads, Desserts, Beverages)
├── requirements.txt     # Python dependencies
├── state.py             # LangGraph state schema definition
├── tools.py             # take_order, cook, and serve tools
├── decision.py          # Decision nodes and flow routing
├── agent.py             # LangGraph workflow, Groq LLM node, and interactive CLI
└── test_agent.py        # Automated test suite covering all decision rules
```

---

## 🛠️ Setup & Installation

1. **Environment Setup**:
   Ensure `.env` contains your `GROQ_API_KEY`:
   ```env
   GROQ_API_KEY=your_groq_api_key
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Interactive CLI**:
   ```bash
   python agent.py
   ```

4. **Run Test Suite**:
   ```bash
   python test_agent.py
   ```

---

## 💬 System Prompt Schema

The LLM is invoked with JSON inputs formatted per the system prompt schema:
`{"take_order": "true/false", "cook": "true/false", "serve": "true/false"}`

- Negative `take_order` input: `"This item is not available for now for the quantity you've asked for. Please lower the quantity or order something else :)"`
- Negative `cook` input: `"Some error occured while cooking this please contact the staff."`
- Fallback / Invalid input: `"This query is invalid, please write a valid query."`