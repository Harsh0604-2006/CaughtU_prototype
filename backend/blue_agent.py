"""
Blue Agent Module
Handles generating human-executable remediation playbooks and applying fixes to the production graph.
Integrates with dynamic risk scoring system for severity-aware remediation.
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
        
    def generate_playbook(self, attack_vector: Dict[str, Any], server_properties: Dict[str, Any], risk_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate remediation playbook using LLM with dynamic risk scoring context.
        
        Args:
            attack_vector: Attack vector details from Red Agent
            server_properties: Target server properties including risk_score
            risk_context: Risk scoring metadata (blast_radius_count, cvss_score, etc.)
            
        Returns:
            Remediation playbook with risk-aware severity levels
        """
        server_name = server_properties.get('name')
        risk_score = server_properties.get('risk_score', 0)
        
        logger.info(f"Blue Agent generating playbook for server {server_name} (risk_score={risk_score})")
        
        # Enrich the payload with risk context for LLM
        enriched_context = {
            "attack_vector": attack_vector,
            "server_properties": server_properties,
            "risk_score": risk_score,
            "severity_level": self._determine_severity_level(risk_score),
            "risk_context": risk_context or {}
        }
        
        result = self.llm.generate_remediation_playbook(enriched_context['attack_vector'], enriched_context['server_properties'])
        
        # Annotate result with risk metadata
        if isinstance(result, dict):
            result['risk_score'] = risk_score
            result['severity_level'] = enriched_context['severity_level']
            result['blast_radius_context'] = risk_context.get('blast_radius_count', 0) if risk_context else 0
        
        return result
    
    def _determine_severity_level(self, risk_score: float) -> str:
        """
        Determine severity level based on dynamic risk score.
        
        Args:
            risk_score: Risk score from 0-100
            
        Returns:
            Severity level string: CRITICAL, HIGH, MEDIUM, LOW
        """
        if risk_score >= 80:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
        
    def apply_fix(self, server_name: str, graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
        """
        Apply fix on the specified graph by isolating the compromised node.
        Uses dynamic risk scoring to determine isolation scope.
        Deletes all edges so the node can't affect other nodes.
        
        Args:
            server_name: Name of the server to isolate
            graph_name: Target graph, defaults to 'prod'
            
        Returns:
            Dictionary with isolation result and risk context
        """
        logger.info(f"Blue Agent applying fix to {graph_name} graph for server {server_name}")
        
        result = {
            "server_name": server_name,
            "graph_name": graph_name,
            "status": "failed",
            "edges_deleted": 0,
            "risk_score_before": None,
            "risk_score_after": None
        }
        
        try:
            # Get risk context before isolation
            with self.neo4j.driver.session() as session:
                pre_query = "MATCH (s:Server {name: $name}) RETURN s.risk_score as risk_score"
                pre_result = session.run(pre_query, name=server_name)
                pre_record = pre_result.single()
                if pre_record:
                    result['risk_score_before'] = pre_record['risk_score']
            
            # Apply isolation: delete all edges connected to the target server
            query = f"""
            MATCH (s:Server {{name: $server_name}})
            OPTIONAL MATCH (s)-[r]-()
            WITH s, collect(DISTINCT r) AS rels, count(DISTINCT r) AS deleted_count
            FOREACH (rel IN rels | DELETE rel)
            SET s.status = 'Isolated',
                s.compromised = true,
                s.isolation_timestamp = datetime()
            RETURN s.name as name, deleted_count
            """
            
            with self.neo4j.driver.session() as session:
                iso_result = session.run(query, server_name=server_name)
                record = iso_result.single()
                if record:
                    result['edges_deleted'] = record.get('deleted_count', 0)
                    
                    # Get risk score after isolation
                    post_query = "MATCH (s:Server {name: $name}) RETURN s.risk_score as risk_score"
                    post_result = session.run(post_query, name=server_name)
                    post_record = post_result.single()
                    if post_record:
                        result['risk_score_after'] = post_record['risk_score']
                    
                    result['status'] = 'success'
                    logger.info(f"Successfully isolated {server_name} in {graph_name}")
                    return result
                else:
                    logger.warning(f"No edges deleted for {server_name}, or node not found in {graph_name}")
                    return result
        except Exception as e:
            logger.error(f"Error applying fix: {str(e)}")
            result['error'] = str(e)
            return result
