"""
Blue Agent Module
Defensive security orchestrator for remediation and isolation
Analyzes Red Agent findings and applies defensive measures
Flow: Receive Attack Vector → Generate Risk-Aware Playbook → Apply Isolation
"""
from typing import List, Dict, Any, Optional
import json
from neo4j_client import Neo4jClient
from llm_client import LLMClient
from config import SIMULATION_GRAPH, PRODUCTION_GRAPH, DEFAULT_GRAPH
import logging

logger = logging.getLogger(__name__)

class BlueAgent:
    """
    Blue Agent for defensive security and remediation
    Generates risk-aware playbooks and isolates compromised nodes
    Adapts to any graph schema dynamically
    """
    
    def __init__(self):
        """Initialize Blue Agent with Neo4j and LLM clients"""
        self.neo4j = Neo4jClient()
        self.llm = LLMClient()
        
    def analyze_threats(self, graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
        """
        Blue Agent threat analysis - identify high-risk nodes requiring remediation
        
        Args:
            graph_name: "prod" or "sim" graph to analyze
        
        Returns:
            Prioritized list of threats with severity levels
        """
        logger.info(f"Blue Agent analyzing threats on {graph_name} graph")
        
        try:
            # Get high-risk nodes from Neo4j
            high_risk_nodes = self.neo4j.get_high_criticality_servers(graph_name=graph_name)
            
            if not high_risk_nodes:
                logger.warning(f"No high-risk nodes found in {graph_name}")
                return {
                    "status": "success",
                    "threats_count": 0,
                    "threats": [],
                    "graph": graph_name
                }
            
            # Enrich with severity levels and CVE context
            threats = []
            for node in high_risk_nodes:
                threat = {
                    "name": node.get("name"),
                    "risk_score": node.get("risk_score", 0),
                    "severity_level": self._determine_severity_level(node.get("risk_score", 0)),
                    "type": node.get("type"),
                    "cvss_score": node.get("cvss_score"),
                    "cve_id": node.get("cve_id"),
                    "status": node.get("status")
                }
                threats.append(threat)
            
            # Sort by severity
            threats.sort(key=lambda t: t["risk_score"], reverse=True)
            
            logger.info(f"Found {len(threats)} high-risk nodes")
            return {
                "status": "success",
                "graph": graph_name,
                "threats_count": len(threats),
                "threats": threats
            }
        
        except Exception as e:
            logger.error(f"Threat analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "threats_count": 0,
                "threats": []
            }
    
    def get_isolation_impact(self, server_name: str, graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
        """
        Analyze impact of isolating a specific node - how many nodes will be affected
        
        Args:
            server_name: Name of the node to isolate
            graph_name: Graph to analyze
        
        Returns:
            Impact analysis with affected nodes and risk reduction
        """
        logger.info(f"Blue Agent analyzing isolation impact for {server_name}")
        
        try:
            # Get blast radius (nodes that depend on this server)
            blast_radius = self.neo4j.get_blast_radius(server_name, graph_name=graph_name)
            
            # Get current risk score
            with self.neo4j.driver.session() as session:
                result = session.run(
                    "MATCH (n {name: $name}) RETURN n.risk_score as risk_score, labels(n) as labels",
                    {"name": server_name}
                )
                record = result.single()
                if not record:
                    return {
                        "status": "error",
                        "message": f"Node {server_name} not found",
                        "affected_nodes": []
                    }
                
                current_risk = record.get("risk_score", 0)
            
            return {
                "status": "success",
                "server_name": server_name,
                "current_risk_score": current_risk,
                "affected_nodes_count": len(blast_radius),
                "affected_nodes": blast_radius,
                "severity_level": self._determine_severity_level(current_risk),
                "isolation_recommended": current_risk >= 50
            }
        
        except Exception as e:
            logger.error(f"Impact analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "affected_nodes": []
            }
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
    
    def close(self):
        """Close database connection"""
        if self.neo4j and hasattr(self.neo4j, 'close'):
            self.neo4j.close()
        logger.info("Blue Agent closed")


def run_blue_agent_threat_analysis(graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run Blue Agent threat analysis
    
    Args:
        graph_name: "prod" or "sim"
    
    Returns:
        Threat analysis results
    """
    agent = BlueAgent()
    try:
        result = agent.analyze_threats(graph_name=graph_name)
        return result
    finally:
        agent.close()


def run_blue_agent_isolation(server_name: str, graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run Blue Agent isolation
    
    Args:
        server_name: Server to isolate
        graph_name: "prod" or "sim"
    
    Returns:
        Isolation result
    """
    agent = BlueAgent()
    try:
        result = agent.apply_fix(server_name=server_name, graph_name=graph_name)
        return result
    finally:
        agent.close()

