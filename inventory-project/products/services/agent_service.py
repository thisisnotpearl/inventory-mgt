import os
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from products.services.agent_tools import get_product_info, check_inventory, calculate_quote

class AgentService:
    """
    Orchestrates the LangChain Tool-Calling Agent using LangGraph.
    """
    
    SYSTEM_PROMPT = """You are an expert Sales Agent for the Toy Store.
Your job is to help customers get quotes for products.

Always follow this strict process when asked for a quote:
1. Use `get_product_info` to find the exact Product ID and Price based on the customer's description.
2. Use `check_inventory` to ensure we have enough stock for their requested quantity.
3. If stock is sufficient, use `calculate_quote` to generate the final price.
4. If the user asks for a discount, pass that percentage to `calculate_quote`. DO NOT do the math yourself. The tool will enforce company policies.
5. If the `calculate_quote` tool returns a POLICY_VIOLATION error, you must apologize to the user and offer the maximum allowed discount.
6. Present the final quote to the user clearly.

Do not guess Product IDs or prices. Always use the tools.
"""
    
    @staticmethod
    def get_agent_executor():
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not found in environment.")

        llm = ChatGroq(
            api_key=api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.0
        )

        tools = [get_product_info, check_inventory, calculate_quote]

        # In very old versions of LangGraph, state_modifier and messages_modifier do not exist.
        # We will simply pass the tools to create_react_agent.
        agent = create_react_agent(llm, tools)
        return agent

    @staticmethod
    def run_agent(user_input: str, chat_history: list = None) -> dict:
        if chat_history is None:
            chat_history = []
            
        # Instead of passing the system prompt to the agent factory, 
        # we prepend it as the very first message in the chat history.
        formatted_history = [SystemMessage(content=AgentService.SYSTEM_PROMPT)]
        
        for msg in chat_history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            else:
                formatted_history.append(AIMessage(content=msg["content"]))

        formatted_history.append(HumanMessage(content=user_input))

        executor = AgentService.get_agent_executor()
        
        # Run the LangGraph agent
        response = executor.invoke({"messages": formatted_history})
        
        # Parse intermediate steps from the message history
        # (Since we passed history, we only care about messages generated during THIS turn)
        # We slice from len(formatted_history) onwards
        new_messages = response["messages"][len(formatted_history):]
        
        steps = []
        final_answer = "No final answer generated."
        
        for msg in new_messages:
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        steps.append({
                            "tool": tool_call["name"],
                            "tool_input": str(tool_call["args"]),
                            "result": None # will be filled by next ToolMessage
                        })
                if msg.content and not msg.tool_calls:
                    final_answer = msg.content
                    
            elif isinstance(msg, ToolMessage):
                # Find the corresponding step and add the result
                for step in reversed(steps):
                    if step["result"] is None and step["tool"] == msg.name:
                        step["result"] = msg.content
                        break

        # Cleanup any unfulfilled steps
        for step in steps:
            if step["result"] is None:
                step["result"] = "Error: Tool did not return a result."
            
        return {
            "answer": final_answer,
            "steps": steps
        }
