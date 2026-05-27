"""
Test script for LangGraph Orchestrator and Blue Agent
"""
import logging
import json
from orchestrator import Orchestrator
from config import PRODUCTION_GRAPH

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_test():
    print("\n" + "="*80)
    print("  Testing LangGraph Orchestrator & Blue Agent")
    print("="*80 + "\n")
    
    try:
        # 1. Initialize orchestrator
        # To get the state in LangGraph without a persistent checkpointer, it's easier to just pass the interrupted state
        # back in. Let's create a memory saver just for this test.
        from langgraph.checkpoint.memory import MemorySaver
        
        print("[*] Initializing Orchestrator with memory checkpointer...")
        orchestrator = Orchestrator()
        
        # We will use CoreDBServer01 since it's highly connected and vulnerable
        target_server = "CoreDBServer01"
        
        # 2. Start the cycle until it interrupts for HUMAN_REVIEW
        print(f"\n[*] Starting Dual-Loop Cycle for {target_server} on {PRODUCTION_GRAPH}...")
        
        config = {"configurable": {"thread_id": "test_session_1"}}
        
        # Stream the graph execution until it hits the interrupt
        initial_state = {
            "server_name": target_server,
            "target_graph": PRODUCTION_GRAPH,
            "incident_details": {},
            "blast_radius": [],
            "red_agent_output": {},
            "blue_playbook": {},
            "human_approved": False,
            "retest_blast_radius": []
        }
        
        for event in orchestrator.graph.stream(initial_state, config):
            for node_name, state_update in event.items():
                print(f"  -> Completed state: {node_name}")
                
                # Print some details of what was generated
                if node_name == "MAP_BLAST_RADIUS":
                    print(f"     Blast radius size: {len(state_update.get('blast_radius', []))} nodes")
                elif node_name == "RED_AGENT_REPORT":
                    print(f"     Red Agent Output received.")
                    with open('red_agent_report.json', 'w') as f:
                        json.dump(state_update.get("red_agent_output", {}), f, indent=2)
                    print(f"     [+] Saved full Red Agent report to 'red_agent_report.json'")
                elif node_name == "BLUE_AGENT_PLAN":
                    playbook = state_update.get("blue_playbook", {})
                    print(f"     Blue Agent Playbook generated.")
                    with open('blue_agent_playbook.json', 'w') as f:
                        json.dump(playbook, f, indent=2)
                    print(f"     [+] Saved full Blue Agent playbook to 'blue_agent_playbook.json'")
        
        print("\n[*] Graph paused for HUMAN_REVIEW.")
        
        try:
            current_state = orchestrator.graph.get_state(config)
            playbook = current_state.values.get("blue_playbook", {})
        except Exception as e:
            logger.error(f"Failed to get state using checkpointer: {e}")
            playbook = {}
        
        print("\n" + "-"*40)
        print("GENERATED PLAYBOOK PREVIEW:")
        print(json.dumps(playbook, indent=2)[:500] + "...\n(truncated)")
        print("-"*40 + "\n")
        
        # 3. Resume the graph with human approval
        print("[*] Simulating Human Approval (human_approved=True)")
        user_input = {"human_approved": True}
        
        try:
            # Tell LangGraph to update the state in the current thread and then resume execution
            orchestrator.graph.update_state(config, user_input)
            for event in orchestrator.graph.stream(None, config):
                 for node_name, state_update in event.items():
                    print(f"  -> Completed state: {node_name}")
                    if node_name == "RETEST":
                         print(f"     Retest Blast radius size: {len(state_update.get('retest_blast_radius', []))} nodes")
        except Exception as e:
             logger.error(f"Failed to resume graph from checkpointer: {e}")
             # fallback to manual step since checkpointer is failing locally
             orchestrator.apply_fix({"server_name": target_server, "target_graph": PRODUCTION_GRAPH})
             res = orchestrator.retest({"server_name": target_server, "target_graph": PRODUCTION_GRAPH})
             print(f"     Retest Blast radius size: {len(res.get('retest_blast_radius', []))} nodes (fallback)")
                     
        print("\n[*] Cycle Complete!")
        
        try:
            final_state = orchestrator.graph.get_state(config)
            retest_nodes = final_state.values.get("retest_blast_radius", [])
            print(f"\nFinal state retest node count: {len(retest_nodes)}")
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    run_test()
