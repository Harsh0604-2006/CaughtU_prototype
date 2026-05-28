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
from risk_calculator import run_risk_calculation
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

    def generate_playbook(
        self,
        attack_vector: Dict[str, Any],
        server_properties: Dict[str, Any],
        risk_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
        
        raw_result = self.llm.generate_remediation_playbook(enriched_context['attack_vector'], enriched_context['server_properties'])

        # Normalize LLM output: prefer parsed dict, otherwise try to extract JSON from raw_response
        playbook_result: Dict[str, Any] = {}

        if isinstance(raw_result, dict) and raw_result.get('playbook'):
            playbook_result = raw_result
        else:
            # Try to extract JSON blob from possible raw_response
            text = ''
            if isinstance(raw_result, dict):
                # common keys: raw_response or parse_error
                text = raw_result.get('raw_response') or raw_result.get('response') or ''
            elif isinstance(raw_result, str):
                text = raw_result

            if text:
                # Remove markdown fences if present
                cleaned = text.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                elif cleaned.startswith('```'):
                    cleaned = cleaned[3:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]

                # Attempt to find the first JSON object
                try:
                    first = cleaned.find('{')
                    last = cleaned.rfind('}')
                    if first != -1 and last != -1 and last > first:
                        json_str = cleaned[first:last+1]
                        import json as _json
                        playbook_result = _json.loads(json_str)
                    else:
                        playbook_result = {'raw_response': text}
                except Exception:
                    playbook_result = {'raw_response': text}
            else:
                playbook_result = {'raw_response': str(raw_result)}

        # Enrich and ensure keys exist
        try:
            playbook_result.setdefault('playbook', playbook_result.get('playbook', []))
            playbook_result['total_remediation_time'] = playbook_result.get('total_remediation_time', 'unknown')
            playbook_result['risk_level_before'] = playbook_result.get('risk_level_before', 'Unknown')
            playbook_result['risk_level_after'] = playbook_result.get('risk_level_after', 'Unknown')
            playbook_result['validation_checklist'] = playbook_result.get('validation_checklist', [])

            # Add risk metadata from server_properties / risk_context
            playbook_result['risk_score'] = server_properties.get('risk_score', risk_score)
            playbook_result['severity_level'] = self._determine_severity_level(playbook_result['risk_score'])
            playbook_result['blast_radius_context'] = risk_context.get('blast_radius_count', 0) if risk_context else playbook_result.get('blast_radius_context', 0)
        except Exception:
            pass

        return playbook_result
    
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
                pre_query = "MATCH (s {name: $name}) RETURN s.risk_score as risk_score"
                pre_result = session.run(pre_query, name=server_name)
                pre_record = pre_result.single()
                if pre_record:
                    result['risk_score_before'] = pre_record['risk_score']
            
            # Apply isolation: delete all edges connected to the target node.
            # This is label-agnostic because graph schema may not use :Server.
            query = """
            MATCH (s {name: $server_name})
            OPTIONAL MATCH (s)-[r]-()
            WITH s, collect(DISTINCT r) AS rels, count(DISTINCT r) AS deleted_count
            FOREACH (rel IN rels | DELETE rel)
            SET s.status = 'Isolated',
                s.compromised = true,
                s.isolated = true,
                s.isolation_timestamp = datetime()
            RETURN s.name as name, deleted_count
            """
            
            with self.neo4j.driver.session() as session:
                iso_result = session.run(query, server_name=server_name)
                record = iso_result.single()
                if record:
                    result['edges_deleted'] = record.get('deleted_count', 0)

                    # Recalculate risk scores after isolation to reflect impact
                    try:
                        run_risk_calculation(graph_name=graph_name)
                    except Exception:
                        logger.warning("Post-fix risk recalculation failed or skipped")

                    # Get risk score after isolation (after recalculation)
                    post_query = "MATCH (s {name: $name}) RETURN s.risk_score as risk_score"
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

