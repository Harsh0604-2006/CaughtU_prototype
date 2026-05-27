"""
Neo4j Client Module
Handles connection to Neo4j AuraDB and executes Cypher queries
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, SIMULATION_GRAPH, PRODUCTION_GRAPH, DEFAULT_GRAPH
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
    
    def get_servers(self, graph_name: str = DEFAULT_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch all relevant nodes from Neo4j - adapts to any schema
        Returns nodes sorted by risk_score (highest first)
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of node dictionaries with properties
        """
        try:
            with self.driver.session() as session:
                # Simpler query - get all nodes with basic properties
                query = """
                MATCH (n)
                RETURN {
                    name: n.name,
                    type: n.type,
                    labels: labels(n),
                    risk_score: n.risk_score,
                    incoming: n.incoming_relationship_count,
                    blast_radius: n.blast_radius_count,
                    cvss_score: n.cvss_score,
                    status: n.status
                } as node_data
                ORDER BY n.risk_score DESC
                LIMIT 100
                """
                
                result = session.run(query)
                servers = []
                
                for record in result:
                    try:
                        node_data = record.get("node_data")
                        if node_data:
                            servers.append(node_data)
                    except Exception as e:
                        logger.warning(f"Failed to process record: {str(e)}")
                        continue
            
            logger.info(f"Fetched {len(servers)} nodes from {graph_name} graph")
            return servers
            
        except Exception as e:
            logger.error(f"Error fetching servers: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def discover_schema(self) -> Dict[str, Any]:
        """
        Dynamically discover the live Neo4j schema
        
        Returns:
            Dictionary with node labels, relationship types, and node properties
        """
        labels = []
        relationship_types = []
        node_properties = {}
        
        try:
            with self.driver.session() as session:
                # Get all node labels
                try:
                    labels_result = session.run("CALL db.labels()")
                    labels = [record[0] for record in labels_result]
                    logger.info(f"Discovered {len(labels)} node labels")
                except Exception as e:
                    logger.warning(f"Failed to get labels: {str(e)}")
                
                # Get all relationship types
                try:
                    rel_result = session.run("CALL db.relationshipTypes()")
                    relationship_types = [record[0] for record in rel_result]
                    logger.info(f"Discovered {len(relationship_types)} relationship types")
                except Exception as e:
                    logger.warning(f"Failed to get relationship types: {str(e)}")
                
                # Try to get node properties (non-critical if it fails)
                try:
                    properties_result = session.run("CALL db.schema.nodeTypeProperties()")
                    for record in properties_result:
                        label = record.get("nodeType", "Unknown")
                        if label not in node_properties:
                            node_properties[label] = []
                        node_properties[label].append({
                            "property": record.get("propertyName", record.get("property")),
                            "type": record.get("propertyTypes", record.get("type"))
                        })
                    logger.info(f"Discovered properties for {len(node_properties)} labels")
                except Exception as e:
                    logger.warning(f"Could not get detailed node properties: {str(e)}")
                
                schema = {
                    "node_labels": labels,
                    "relationship_types": relationship_types,
                    "node_properties": node_properties
                }
                
                logger.info(f"Schema discovered: {len(labels)} node labels, {len(relationship_types)} relationship types")
                return schema
        
        except Exception as e:
            logger.error(f"Schema discovery error: {str(e)}")
            return {
                "node_labels": labels,
                "relationship_types": relationship_types,
                "node_properties": node_properties
            }
    
    def execute_custom_cypher(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom Cypher query generated by LLM
        
        Args:
            cypher_query: The Cypher query to execute
            parameters: Optional parameters for the query
        
        Returns:
            Query results as list of dictionaries
        """
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})
                results = [dict(record) for record in result]
            
            logger.info(f"Custom Cypher executed, returned {len(results)} results")
            return results
        
        except Exception as e:
            logger.error(f"Cypher execution failed: {str(e)}")
            return []
    
    def get_vulnerabilities_for_servers(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch nodes with CVE/vulnerability data from Neo4j
        Adapts to whatever schema exists - looks for cvss_score, cve_id, exploit_available
        
        Args:
            servers: List of node dictionaries
        
        Returns:
            List of nodes with CVE data
        """
        try:
            query = """
            MATCH (n)
            WHERE n.cvss_score IS NOT NULL OR n.cve_id IS NOT NULL OR n.exploit_available IS NOT NULL
            RETURN {
                name: n.name,
                type: n.type,
                labels: labels(n),
                cvss_score: n.cvss_score,
                cve_id: n.cve_id,
                exploit_available: n.exploit_available,
                attack_vector: n.attack_vector,
                risk_score: n.risk_score,
                status: n.status
            } as node_data
            ORDER BY n.cvss_score DESC
            LIMIT 100
            """
            
            with self.driver.session() as session:
                result = session.run(query)
                vulnerabilities = []
                for record in result:
                    try:
                        node_data = record.get("node_data")
                        if node_data:
                            vulnerabilities.append(node_data)
                    except Exception as e:
                        logger.warning(f"Failed to process vulnerability record: {str(e)}")
                        continue
            
            logger.info(f"Fetched {len(vulnerabilities)} nodes with CVE data from Neo4j")
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Error fetching vulnerabilities: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_blast_radius(self, server_name: str, graph_name: str = DEFAULT_GRAPH) -> List[Dict[str, Any]]:
        """
        Calculate blast radius using Cypher traversal
        Returns all nodes reachable from the compromised node (both directions)
        If direct traversal returns no results, shows nodes with incoming/outgoing relationships
        
        Args:
            server_name: Name of the compromised node
            graph_name: Graph to query
        
        Returns:
            List of affected nodes with their properties
        """
        # First try: bidirectional traversal from the start node
        query1 = """
        MATCH (start {name: $server_name})
        MATCH (start)-[*1..5]-(affected)
        WHERE affected.name <> $server_name
        RETURN DISTINCT {
            name: affected.name,
            labels: labels(affected),
            type: affected.type,
            risk_score: affected.risk_score,
            criticality: affected.criticality,
            status: affected.status
        } as node_data
        LIMIT 100
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query1, server_name=server_name)
                blast_radius = []
                for record in result:
                    try:
                        node_data = record.get("node_data")
                        if node_data:
                            blast_radius.append(node_data)
                    except Exception as e:
                        logger.warning(f"Failed to process blast radius record: {str(e)}")
                        continue
                
                if blast_radius:
                    logger.info(f"Blast radius from {server_name}: {len(blast_radius)} nodes affected (traversal)")
                    return blast_radius
            except Exception as e:
                logger.warning(f"Bidirectional traversal failed for {server_name}: {str(e)}")
        
        # Fallback: if traversal found nothing, find directly connected nodes
        query2 = """
        MATCH (start {name: $server_name})
        MATCH (start)--(connected)
        WHERE connected.name <> $server_name
        RETURN DISTINCT {
            name: connected.name,
            labels: labels(connected),
            type: connected.type,
            risk_score: connected.risk_score,
            criticality: connected.criticality,
            status: connected.status,
            connection_type: "direct"
        } as node_data
        LIMIT 100
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query2, server_name=server_name)
                blast_radius = []
                for record in result:
                    try:
                        node_data = record.get("node_data")
                        if node_data:
                            blast_radius.append(node_data)
                    except Exception as e:
                        logger.warning(f"Failed to process direct connection record: {str(e)}")
                        continue
                
                if blast_radius:
                    logger.info(f"Blast radius from {server_name}: {len(blast_radius)} nodes affected (direct connections)")
                    return blast_radius
            except Exception as e:
                logger.warning(f"Direct connection query failed for {server_name}: {str(e)}")
        
        logger.info(f"Blast radius from {server_name}: 0 nodes affected (no connections found)")
        return []
    
    def get_high_criticality_servers(self, graph_name: str = DEFAULT_GRAPH) -> List[Dict[str, Any]]:
        """
        Fetch highest-risk nodes from any schema
        Adapts to whatever properties exist (risk_score, criticality, etc.)
        
        Args:
            graph_name: Either "prod" or "sim"
        
        Returns:
            List of high-risk nodes ordered by risk
        """
        # Query for nodes with highest risk_score
        query = """
        MATCH (n)
        WHERE n.risk_score IS NOT NULL
        RETURN n.name as name,
               n.risk_score as risk_score,
               n.incoming_relationship_count as incoming,
               n.blast_radius_count as blast_radius,
               n.cvss_score as cvss_score,
               n.type as type,
               labels(n) as node_type
        ORDER BY n.risk_score DESC
        LIMIT 50
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            nodes = [dict(record) for record in result]
        
        return nodes
    
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
