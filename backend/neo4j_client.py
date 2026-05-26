"""
Neo4j Client Module
Handles connection to Neo4j AuraDB and executes Cypher queries
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, SIMULATION_GRAPH, PRODUCTION_GRAPH
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Client for Neo4j database operations"""
    
    def __init__(self):
        """Initialize Neo4j driver"""
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    
    def close(self):
        """Close the driver connection"""
        self.driver.close()
    
    def get_servers(self, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch all server nodes from Neo4j
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of server dictionaries with properties
        """
        query = f"""
        MATCH (s:Server {{graph: "{graph_name}"}})
        RETURN s.name as name,
               s.product as product,
               s.version as version,
               s.ip as ip,
               s.os as os,
               s.criticality as criticality,
               s.zone as zone
        ORDER BY s.criticality DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            servers = [dict(record) for record in result]
        
        logger.info(f"Fetched {len(servers)} servers from {graph_name} graph")
        return servers
    
    def get_vulnerabilities_for_servers(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch vulnerabilities for the given servers
        
        Args:
            servers: List of server dictionaries
        
        Returns:
            List of vulnerability relationships
        """
        query = """
        MATCH (s:Server {graph: $graph})-[v:HAS_VULNERABILITY]->(vuln:Vulnerability)
        WHERE s.name IN $server_names
        RETURN s.name as server_name,
               s.criticality as server_criticality,
               vuln.cve_id as cve_id,
               vuln.cvss_score as cvss_score,
               vuln.attack_vector as attack_vector,
               vuln.attack_complexity as attack_complexity,
               vuln.exploit_available as exploit_available
        ORDER BY vuln.cvss_score DESC
        """
        
        server_names = [s['name'] for s in servers]
        
        with self.driver.session() as session:
            result = session.run(
                query,
                graph=PRODUCTION_GRAPH,
                server_names=server_names
            )
            vulnerabilities = [dict(record) for record in result]
        
        logger.info(f"Fetched {len(vulnerabilities)} vulnerabilities for servers")
        return vulnerabilities
    
    def get_blast_radius(self, server_name: str, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Calculate blast radius using Cypher traversal
        Returns all nodes reachable from the compromised server
        
        Args:
            server_name: Name of the compromised server
            graph_name: Graph to query
        
        Returns:
            List of affected nodes
        """
        query = f"""
        MATCH (start:Server {{name: $server_name, graph: "{graph_name}"}})
        MATCH (start)-[*1..5]->(affected)
        WHERE affected.graph = "{graph_name}"
        RETURN DISTINCT affected.name as name,
                        labels(affected) as labels,
                        affected.criticality as criticality
        ORDER BY affected.criticality DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, server_name=server_name)
            blast_radius = [dict(record) for record in result]
        
        logger.info(f"Blast radius from {server_name}: {len(blast_radius)} nodes affected")
        return blast_radius
    
    def get_high_criticality_servers(self, graph_name: str = PRODUCTION_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch high/critical criticality servers
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of high-priority servers
        """
        query = f"""
        MATCH (s:Server {{graph: "{graph_name}"}})
        WHERE s.criticality IN ["Critical", "High"]
        RETURN s.name as name,
               s.product as product,
               s.version as version,
               s.ip as ip,
               s.criticality as criticality
        ORDER BY s.criticality DESC, s.name
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            servers = [dict(record) for record in result]
        
        return servers
    
    def check_connection(self) -> bool:
        """
        Test connection to Neo4j
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            return True
        except Exception as e:
            logger.error(f"Neo4j connection failed: {str(e)}")
            return False
