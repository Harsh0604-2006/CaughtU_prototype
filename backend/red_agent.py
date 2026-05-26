"""
Red Agent Module
Main orchestrator for attack vector analysis and prioritization
Flow: Neo4j Servers → NVD CVEs → LLM Analysis → Prioritized Attack Vectors
"""
from typing import List, Dict, Any, Optional
from neo4j_client import Neo4jClient
from nvd_client import NVDClient
from llm_client import LLMClient
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH, MAX_ATTACK_VECTORS, CVSS_THRESHOLD
import logging

logger = logging.getLogger(__name__)


class RedAgent:
    """
    Red Agent for attack vector analysis
    Combines Neo4j topology, NVD CVE data, and LLM intelligence
    to identify and prioritize attack vectors
    """
    
    def __init__(self):
        """Initialize Red Agent with clients"""
        self.neo4j = Neo4jClient()
        self.nvd = NVDClient()
        self.llm = LLMClient()
    
    def analyze_attack_vectors(
        self,
        graph_name: str = PRODUCTION_GRAPH,
        focus_server: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main method to analyze and prioritize attack vectors
        Dynamically adapts to whatever schema exists in Neo4j
        
        Args:
            graph_name: "prod" or "sim" graph to analyze
            focus_server: Optional specific node to focus on
        
        Returns:
            Structured attack vector analysis with prioritization
        """
        logger.info(f"Red Agent starting analysis on {graph_name} graph (schema-agnostic)")
        
        try:
            # Step 1: Fetch all nodes from Neo4j (Device, Server, etc.)
            logger.info("Step 1: Fetching nodes from Neo4j")
            nodes = self.neo4j.get_servers(graph_name=graph_name)
            
            if not nodes:
                logger.error("No nodes found in graph")
                return {
                    "status": "error",
                    "message": "No nodes found in graph",
                    "nodes_analyzed": 0
                }
            
            logger.info(f"Found {len(nodes)} nodes")
            
            # Step 2: Get relationships/connections for these nodes
            logger.info("Step 2: Fetching relationships from Neo4j")
            relationships = self.neo4j.get_vulnerabilities_for_servers(nodes)
            logger.info(f"Found {len(relationships)} relationships")
            
            # Step 3: Enrich with NVD CVE data (static cache)
            logger.info("Step 3: Enriching with NVD CVE data")
            enriched_vulns = self._enrich_vulnerabilities(nodes, relationships)
            logger.info(f"Enriched {len(enriched_vulns)} entries")
            
            # Step 4: Calculate blast radius for critical nodes
            logger.info("Step 4: Calculating blast radius")
            blast_radii = self._calculate_blast_radii(nodes, graph_name)
            
            # Step 5: Use LLM to prioritize attack vectors
            logger.info("Step 5: Using LLM to prioritize attack vectors")
            attack_analysis = self.llm.prioritize_attack_vectors(
                servers=nodes,
                vulnerabilities=enriched_vulns,
                blast_radius=blast_radii
            )
            
            # Step 6: Format final output
            result = {
                "status": "success",
                "graph": graph_name,
                "nodes_analyzed": len(nodes),
                "entries_enriched": len(enriched_vulns),
                "high_risk_nodes": self._identify_high_risk_servers(enriched_vulns),
                "attack_vectors": attack_analysis.get("attack_vectors", []),
                "executive_summary": attack_analysis.get("executive_summary", ""),
                "defensive_priorities": attack_analysis.get("defensive_priorities", []),
                "blast_radii_summary": blast_radii,
                "neo4j_relationships": relationships
            }
            
            logger.info("Red Agent analysis complete")
            return result
        
        except Exception as e:
            logger.error(f"Red Agent analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "servers_analyzed": 0
            }
    
    def _enrich_vulnerabilities(
        self,
        nodes: List[Dict[str, Any]],
        vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich Neo4j vulnerabilities with additional NVD context
        
        Args:
            nodes: List of nodes from Neo4j
            vulnerabilities: List of vulnerabilities from Neo4j HAS_VULNERABILITY relationships
        
        Returns:
            Enriched vulnerability data
        """
        enriched = []
        
        if not vulnerabilities:
            logger.info("No vulnerabilities found in Neo4j, generating from NVD cache")
            # If no vulnerabilities in Neo4j, create entries from NVD cache for all products
            products_in_graph = set()
            for node in nodes:
                if node.get('product'):
                    products_in_graph.add(node['product'])
            
            for product in products_in_graph:
                cves = self.nvd.get_cves_for_product(product, "")
                for cve in cves[:3]:  # Top 3 per product
                    enriched.append({
                        "source_name": "NVD_Cache",
                        "vuln_name": cve.get('name'),
                        "cve_id": cve.get('cve_id'),
                        "cvss_score": cve.get('cvss_score'),
                        "description": cve.get('description'),
                        "product": product,
                        "source": "NVD"
                    })
            return enriched
        
        # Process vulnerabilities from Neo4j
        for vuln in vulnerabilities:
            source_name = vuln.get('source_name', '')
            source_node = next((n for n in nodes if n.get('name') == source_name), None)
            
            # Build enriched entry
            enriched_vuln = {
                "source_name": source_name,
                "source_type": vuln.get('source_type'),
                "source_product": source_node.get('product') if source_node else None,
                "source_criticality": source_node.get('criticality') if source_node else None,
                "vuln_name": vuln.get('vuln_name'),
                "cve_id": vuln.get('cve_id'),
                "cvss_score": vuln.get('cvss_score'),
                "attack_vector": vuln.get('attack_vector'),
                "attack_complexity": vuln.get('attack_complexity'),
                "exploit_available": vuln.get('exploit_available'),
                "description": vuln.get('description'),
                "all_properties": vuln.get('all_properties'),
                "source": "Neo4j"
            }
            
            enriched.append(enriched_vuln)
        
        logger.info(f"Enriched {len(enriched)} vulnerabilities from Neo4j")
        return enriched
    
    def _calculate_blast_radii(
        self,
        nodes: List[Dict[str, Any]],
        graph_name: str
    ) -> Dict[str, List[str]]:
        """
        Calculate blast radius for each high-risk node (schema-agnostic)
        
        Args:
            nodes: List of nodes from Neo4j (Device, Server, etc.)
            graph_name: Graph to query
        
        Returns:
            Dictionary mapping node names to their blast radii
        """
        blast_radii = {}
        
        # Focus on critical/high criticality nodes
        high_risk = [n for n in nodes if n.get('criticality') in ['Critical', 'High', 'CRITICAL', 'HIGH']]
        
        for node in high_risk[:10]:  # Limit to first 10 to save time
            node_name = node.get('name')
            
            try:
                blast_radius = self.neo4j.get_blast_radius(node_name, graph_name)
                affected_nodes = [n.get('name') for n in blast_radius]
                blast_radii[node_name] = affected_nodes
                
                logger.info(f"Blast radius for {node_name}: {len(affected_nodes)} nodes affected")
            
            except Exception as e:
                logger.warning(f"Failed to calculate blast radius for {node_name}: {str(e)}")
                blast_radii[node_name] = []
        
        return blast_radii
    
    def _identify_high_risk_servers(
        self,
        vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify servers with highest risk (most vulns, highest CVSS, exploitable)
        
        Args:
            vulnerabilities: List of enriched vulnerabilities
        
        Returns:
            List of high-risk servers sorted by risk
        """
        server_risk = {}
        
        for vuln in vulnerabilities:
            server_name = vuln.get('server_name')
            cvss = vuln.get('cvss_score', 0)
            exploit = vuln.get('exploit_available', False)
            criticality = vuln.get('server_criticality', 'Low')
            
            # Calculate risk score: (CVSS × criticality × exploit)
            criticality_multiplier = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0.5}.get(criticality, 1)
            exploit_multiplier = 1.5 if exploit else 1.0
            risk_score = cvss * criticality_multiplier * exploit_multiplier
            
            if server_name not in server_risk:
                server_risk[server_name] = {
                    'server_name': server_name,
                    'total_vulns': 0,
                    'risk_score': 0,
                    'max_cvss': 0,
                    'exploitable_vulns': 0
                }
            
            server_risk[server_name]['total_vulns'] += 1
            server_risk[server_name]['risk_score'] += risk_score
            server_risk[server_name]['max_cvss'] = max(server_risk[server_name]['max_cvss'], cvss)
            
            if exploit:
                server_risk[server_name]['exploitable_vulns'] += 1
        
        # Sort by risk score
        sorted_servers = sorted(
            server_risk.values(),
            key=lambda x: x['risk_score'],
            reverse=True
        )
        
        return sorted_servers[:5]  # Return top 5 high-risk servers
    
    def close(self):
        """Close all client connections"""
        self.neo4j.close()
        logger.info("Red Agent closed")


# Convenience function for direct usage
def run_red_agent_analysis(graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run red agent analysis
    
    Args:
        graph_name: "prod" or "sim"
    
    Returns:
        Analysis results
    """
    agent = RedAgent()
    try:
        result = agent.analyze_attack_vectors(graph_name=graph_name)
        return result
    finally:
        agent.close()
