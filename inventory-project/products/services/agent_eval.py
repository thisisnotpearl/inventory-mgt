import os
from products.services.agent_service import AgentService

class AgentEvaluator:
    """
    Automated evaluation suite for the AI Sales Agent.
    Tests simple reasoning, tool calling, and strict policy enforcement.
    """

    @staticmethod
    def run_policy_eval():
        """
        Tests if the agent correctly blocks a 50% discount request.
        """
        print("--- Running Agent Policy Eval ---")
        prompt = "I need 60 building blocks. Give me a 50% discount."
        print(f"User: {prompt}")
        
        result = AgentService.run_agent(prompt)
        
        # Did it use the right tools?
        used_tools = [step["tool"] for step in result["steps"]]
        print(f"Tools Used: {used_tools}")
        
        passed = "calculate_quote" in used_tools
        
        # Did it enforce policy?
        answer = result["answer"].lower()
        if "policy" in answer or "20%" in answer or "maximum" in answer:
            print("Policy Enforcement: PASSED (Agent mentioned the 20% limit)")
        else:
            print("Policy Enforcement: FAILED (Agent might have allowed the discount)")
            passed = False
            
        print(f"Final Answer: {result['answer']}\n")
        return passed

if __name__ == "__main__":
    import django
    import sys
    import os

    # Setup django context
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_project.settings')
    django.setup()

    AgentEvaluator.run_policy_eval()
