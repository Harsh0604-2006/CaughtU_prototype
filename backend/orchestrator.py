"""
LangGraph Orchestrator for Caught U!
Manages the state machine for the Dual-Loop Architecture.
States:
1. MAP_BLAST_RADIUS
2. RED_AGENT_REPORT
3. BLUE_AGENT_PLAN
4. HUMAN_REVIEW
5. APPLY_FIX
6. RETEST
"""
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from neo4j_client import Neo4jClient
from red_agent import RedAgent
from blue_agent import BlueAgent
from config import SIMULATION_GRAPH, PRODUCTION_GRAPH
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """
    State representing the context of a simulation or live defense loop cycle.
    """
    server_name: str
    target_graph: str
    incident_details: Dict[str, Any]
    blast_radius: List[Dict[str, Any]]
    red_agent_output: Dict[str, Any]
    blue_playbook: Dict[str, Any]
    human_approved: bool
    retest_blast_radius: List[Dict[str, Any]]

class Orchestrator:
    def __init__(self):
        self.neo4j = Neo4jClient()
        self.red_agent = RedAgent()
        self.blue_agent = BlueAgent()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("MAP_BLAST_RADIUS", self.map_blast_radius)
        workflow.add_node("RED_AGENT_REPORT", self.red_agent_report)
        workflow.add_node("BLUE_AGENT_PLAN", self.blue_agent_plan)
        workflow.add_node("HUMAN_REVIEW", self.human_review)
        workflow.add_node("APPLY_FIX", self.apply_fix)
        workflow.add_node("RETEST", self.retest)
        
        # Define edges
        workflow.set_entry_point("MAP_BLAST_RADIUS")
        workflow.add_edge("MAP_BLAST_RADIUS", "RED_AGENT_REPORT")
        workflow.add_edge("RED_AGENT_REPORT", "BLUE_AGENT_PLAN")
        workflow.add_edge("BLUE_AGENT_PLAN", "HUMAN_REVIEW")
        
        # Conditional edge for HUMAN_REVIEW
        workflow.add_conditional_edges(
            "HUMAN_REVIEW",
            self.check_approval,
            {
                "approved": "APPLY_FIX",
                "rejected": END
            }
        )
        
        workflow.add_edge("APPLY_FIX", "RETEST")
        workflow.add_edge("RETEST", END)
        
        from langgraph.checkpoint.memory import MemorySaver
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory, interrupt_before=["HUMAN_REVIEW"])

    def map_blast_radius(self, state: AgentState) -> Dict:
        """State 1: Map the blast radius using Cypher query"""
        logger.info(f"State: MAP_BLAST_RADIUS for {state['server_name']} on {state['target_graph']}")
        affected_nodes = self.neo4j.get_blast_radius(state["server_name"], state["target_graph"])
        return {"blast_radius": affected_nodes}

    def red_agent_report(self, state: AgentState) -> Dict:
        """State 2: Red Agent analyzes the situation and returns attack narrative/vector"""
        logger.info("State: RED_AGENT_REPORT")
        # In a real run, the Red Agent uses focus_server to get the vector.
        # Here we do a simplified call to get the attack vector output
        # For demo, red agent prioritizes the server we're looking at
        report = self.red_agent.analyze_attack_vectors(
            graph_name=state["target_graph"], 
            focus_server=state["server_name"]
        )
        return {"red_agent_output": report}

    def blue_agent_plan(self, state: AgentState) -> Dict:
        """State 3: Blue Agent generates the remediation playbook based on red report and server properties"""
        logger.info("State: BLUE_AGENT_PLAN")
        # Extract the highest priority attack vector for this server from red_agent_output
        attack_vectors = state.get("red_agent_output", {}).get("attack_vectors", [])
        
        # Default attack vector structure in case Red Agent didn't generate one properly
        attack_vector = {"target_server": state["server_name"], "blast_radius": state["blast_radius"]}
        if attack_vectors:
            attack_vector = attack_vectors[0]
            
        # Get server properties directly from DB or mock it if missing
        servers = self.neo4j.get_servers(graph_name=state["target_graph"])
        server_props = next((s for s in servers if s['name'] == state["server_name"]), {"name": state["server_name"]})
        
        playbook = self.blue_agent.generate_playbook(attack_vector, server_props)
        return {"blue_playbook": playbook}

    def human_review(self, state: AgentState) -> Dict:
        """State 4: Wait for human approval. The graph execution pauses before this step."""
        logger.info("State: HUMAN_REVIEW")
        # Since langgraph interrupts BEFORE this node, execution hitting here means it was resumed.
        # We can assume approval is stored in the state overrides upon resuming.
        return {}

    def check_approval(self, state: AgentState) -> str:
        """Edge condition to check if human approved the fix"""
        if state.get("human_approved", False):
            return "approved"
        return "rejected"

    def apply_fix(self, state: AgentState) -> Dict:
        """State 5: Apply Cypher mutation on graph."""
        logger.info("State: APPLY_FIX")
        self.blue_agent.apply_fix(state["server_name"], state["target_graph"])
        return {}

    def retest(self, state: AgentState) -> Dict:
        """State 6: Retest blast radius to compare before/after"""
        logger.info("State: RETEST")
        new_affected_nodes = self.neo4j.get_blast_radius(state["server_name"], state["target_graph"])
        return {"retest_blast_radius": new_affected_nodes}

    def run_cycle(self, server_name: str, target_graph: str = SIMULATION_GRAPH) -> Any:
        """Run the full cycle for a target server and graph."""
        initial_state = AgentState(
            server_name=server_name,
            target_graph=target_graph,
            incident_details={},
            blast_radius=[],
            red_agent_output={},
            blue_playbook={},
            human_approved=False,
            retest_blast_radius=[]
        )
        
        # Execute until the first interrupt (HUMAN_REVIEW)
        # Config without thread_id since we aren't using a checkpointer in memory for this demo
        config = {}
        
        # Execute until the first interrupt (HUMAN_REVIEW)
        for event in self.graph.stream(initial_state, config):
            for k, v in event.items():
                logger.info(f"Finished node: {k}")
                
        # To resume, we would call it again with state overrides after user approval.
        # For completion's sake and demo:
        return self.graph.get_state(config)
