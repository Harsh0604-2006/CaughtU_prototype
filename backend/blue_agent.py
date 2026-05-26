"""
Blue Agent Module
Handles generating human-executable remediation playbooks and applying fixes to the simulation graph.
"""
from typing import List, Dict, Any, Optional
from neo4j_client import Neo4jClient
from llm_client import LLMClient
from config import SIMULATION_GRAPH, PRODUCTION_GRAPH
import logging

logger = logging.getLogger(__name__)

class BlueAgent:
    """
    Blue Agent for remediation analysis
    Combines LLM playbook generation with graph mutation capabilities
    for the simulation environment.
    """
    
    def __init__(self):
        """Initialize Blue Agent with clients"""
        self.neo4j = Neo4jClient()
        self.llm = LLMClient()
        
    def generate_playbook(self, attack_vector: Dict[str, Any], server_properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate remediation playbook using LLM
        """
        logger.info(f"Blue Agent generating playbook for server {server_properties.get('name')}")
        result = self.llm.generate_remediation_playbook(attack_vector, server_properties)
        return result
        
    def apply_fix_simulation(self, server_name: str, graph_name: str = SIMULATION_GRAPH) -> bool:
        """
        Apply fix on simulation graph by isolating the compromised node.
        Deletes CONNECTS_TO edges so it can't affect other nodes.
        
        Args:
            server_name: Name of the server to isolate
            graph_name: Target graph, defaults to 'sim'
            
        Returns:
            Boolean indicating success
        """
        if graph_name == PRODUCTION_GRAPH:
            logger.warning("Attempted to run apply_fix_simulation on PRODUCTION_GRAPH! Denied.")
            return False
            
        logger.info(f"Blue Agent applying fix to {graph_name} graph for server {server_name}")
        
        query = f"""
        MATCH (s:Server {{name: $server_name, graph: '{graph_name}'}})-[r:CONNECTS_TO]-()
        DELETE r
        SET s.status = 'Isolated'
        SET s.compromised = true
        RETURN s.name as name
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query, server_name=server_name)
                record = result.single()
                if record:
                    logger.info(f"Successfully isolated {server_name}")
                    return True
                else:
                    # Node might not have had any connections or might not exist
                    logger.warning(f"No edges deleted for {server_name}, or node not found in {graph_name}")
                    return False
        except Exception as e:
            logger.error(f"Error applying fix: {str(e)}")
            return False
