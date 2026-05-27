"""
Risk Calculator Module - DYNAMIC VERSION
Queries database structure first, then calculates risk scores
Adapts to whatever graph schema exists - NO HARDCODED ASSUMPTIONS
"""
import logging
from typing import Dict, Any
from neo4j_client import Neo4jClient
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH, DEFAULT_GRAPH

logger = logging.getLogger(__name__)


class RiskCalculator:
    """
    Calculates risk scores dynamically by:
    1. Querying what node types exist in database
    2. Querying what relationships exist
    3. Calculating risk from actual graph topology
    4. Using 3 signals: CVE data (if exists), graph position, node properties
    """
    
    def __init__(self):
        """Initialize risk calculator"""
        self.neo4j = Neo4jClient()
        self.node_labels = None
        self.rel_types = None
    
    def _discover_database_structure(self) -> Dict[str, Any]:
        """
        Query database to discover what actually exists
        Returns: {node_labels: [...], relationship_types: [...]}
        """
        logger.info("Discovering database structure...")
        
        with self.neo4j.driver.session() as session:
            # Get all node labels
            labels_result = session.run("CALL db.labels() YIELD label RETURN label")
            self.node_labels = [record["label"] for record in labels_result]
            
            # Get all relationship types
            rels_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
            self.rel_types = [record["relationshipType"] for record in rels_result]
        
        logger.info(f"Found {len(self.node_labels)} node labels: {self.node_labels[:10]}...")
        logger.info(f"Found {len(self.rel_types)} relationship types: {self.rel_types[:10]}...")
        
        return {
            "node_labels": self.node_labels,
            "relationship_types": self.rel_types
        }
    
    def _get_critical_node_types(self) -> list:
        """
        Query database to find critical node types
        Returns list of critical labels discovered
        """
        logger.info("Identifying critical node types...")
        
        # Keywords that indicate criticality
        critical_keywords = ["payment", "treasury", "core", "database", "account", "transaction", "bank", "server", "api", "security"]
        
        # Find labels matching critical keywords
        critical_labels = [label for label in self.node_labels if any(kw in label.lower() for kw in critical_keywords)]
        
        logger.info(f"Critical labels identified: {critical_labels}")
        return critical_labels
    
    def _build_traversal_patterns(self) -> list:
        """
        Find relationship types to use for blast radius calculation
        Returns list of relevant relationship types
        """
        logger.info("Building traversal patterns...")
        
        # Keywords for relationships to traverse
        traversal_keywords = ["connects", "routes", "deploys", "uses", "integrates", "device", "maintains", "operates", "monitors", "syncs", "relays", "access"]
        
        # Find relationships matching traversal keywords
        traversal_rels = [rel for rel in self.rel_types if any(kw in rel.lower() for kw in traversal_keywords)]
        
        logger.info(f"Traversal relationships identified: {traversal_rels[:10]}...")
        return traversal_rels
    
    def recalculate_all_risk_scores(self, graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
        """
        Main orchestrator - recalculate all risk scores
        """
        logger.info(f"Starting dynamic risk calculation for {graph_name} graph")
        
        try:
            # Step 0: Discover what's in the database
            self._discover_database_structure()
            critical_labels = self._get_critical_node_types()
            traversal_rels = self._build_traversal_patterns()
            
            # Step 1: Calculate incoming relationship count (how exposed)
            logger.info("Step 1: Calculating exposure from incoming relationships")
            exposure_count = self._calculate_exposure_scores()
            
            # Step 2: Calculate blast radius (downstream critical nodes)
            logger.info("Step 2: Calculating blast radius to critical nodes")
            blast_count = self._calculate_blast_radius_scores(critical_labels, traversal_rels)
            
            # Step 3: Calculate final risk score
            logger.info("Step 3: Calculating final risk_score from formula")
            risk_count = self._calculate_risk_scores()
            
            # Step 4: Get statistics
            logger.info("Step 4: Gathering statistics")
            stats = self._get_risk_statistics()
            
            result = {
                "status": "success",
                "graph": graph_name,
                "exposure_nodes_updated": exposure_count,
                "blast_radius_nodes_updated": blast_count,
                "risk_score_nodes_updated": risk_count,
                "statistics": stats
            }
            
            logger.info("Risk calculation complete")
            return result
        
        except Exception as e:
            logger.error(f"Risk calculation failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "exposure_nodes_updated": 0,
                "blast_radius_nodes_updated": 0,
                "risk_score_nodes_updated": 0
            }
    
    def _calculate_exposure_scores(self) -> int:
        """
        Signal 1: Graph exposure
        Count incoming relationships to understand how exposed a node is
        """
        query = """
        MATCH (n)
        OPTIONAL MATCH (other)-[r]->(n)
        WITH n, count(r) as incoming_count
        SET n.incoming_relationship_count = incoming_count
        RETURN count(n) as updated_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                count = record.get("updated_count") if record else 0
            logger.info(f"Exposure calculation: Updated {count} nodes")
            return count
        except Exception as e:
            logger.error(f"Exposure calculation failed: {str(e)}")
            return 0
    
    def _calculate_blast_radius_scores(self, critical_labels: list, traversal_rels: list) -> int:
        """
        Signal 2: Graph topology
        Calculate how many critical downstream nodes can be reached
        Uses discovered labels and relationships
        """
        if not critical_labels or not traversal_rels:
            logger.warning("No critical labels or traversal relationships found")
            return 0
        
        # Build Cypher with discovered relationships
        rel_pattern = "|".join(traversal_rels)
        label_filter = "|".join(critical_labels)
        
        query = f"""
        MATCH (n)
        OPTIONAL MATCH (n)-[:{rel_pattern}*1..4]->(reachable)
        WHERE reachable:{label_filter}
        WITH n, count(DISTINCT reachable) as critical_downstream
        SET n.blast_radius_count = critical_downstream
        RETURN count(n) as updated_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                count = record.get("updated_count") if record else 0
            logger.info(f"Blast radius calculation: Updated {count} nodes")
            return count
        except Exception as e:
            logger.error(f"Blast radius calculation failed: {str(e)}")
            # Fallback: just count relationships regardless of label
            return self._calculate_blast_radius_fallback()
    
    def _calculate_blast_radius_fallback(self) -> int:
        """
        Fallback: calculate blast radius by counting all reachable nodes
        """
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[*1..4]->(reachable)
        WITH n, count(DISTINCT reachable) as all_downstream
        SET n.blast_radius_count = all_downstream
        RETURN count(n) as updated_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                count = record.get("updated_count") if record else 0
            logger.info(f"Blast radius (fallback): Updated {count} nodes")
            return count
        except Exception as e:
            logger.error(f"Fallback blast radius failed: {str(e)}")
            return 0
    
    def _calculate_risk_scores(self) -> int:
        """
        Signal 3: Combine all signals into risk score (0-100)
        
        Formula (all signals are DYNAMIC from database):
        - CVE Component (0-40): cvss_score * 4 if exists
        - Exploit Component (0-20): exploit_available = "true"
        - Vector Component (0-20): attack_vector = "Network"
        - Graph Exposure (0-10): incoming relationship count
        - Blast Radius (0-10): downstream critical nodes
        
        Total = min(sum_all, 100)
        """
        query = """
        MATCH (n)
        WITH n,
             // Signal 1: CVE Data (0-40) - FROM DATABASE
             CASE
                 WHEN n.cvss_score IS NOT NULL THEN CASE WHEN TOFLOAT(n.cvss_score) * 4 > 40 THEN 40 ELSE TOFLOAT(n.cvss_score) * 4 END
                 ELSE 0
             END as cve_score,
             
             // Signal 2: Exploit Available (0-20) - FROM DATABASE
             CASE
                 WHEN n.exploit_available = "true" THEN 20
                 ELSE 0
             END as exploit_score,
             
             // Signal 3: Attack Vector (0-20) - FROM DATABASE
             CASE
                 WHEN n.attack_vector = "Network" OR n.attack_vector = "NETWORK" THEN 20
                 ELSE 0
             END as vector_score,
             
             // Signal 4: Graph Exposure (0-10) - CALCULATED FROM GRAPH
             CASE
                 WHEN n.incoming_relationship_count IS NOT NULL THEN CASE WHEN TOFLOAT(n.incoming_relationship_count) > 10 THEN 10 ELSE TOFLOAT(n.incoming_relationship_count) END
                 ELSE 0
             END as exposure_score
        
        WITH n, cve_score, exploit_score, vector_score, exposure_score,
             // Signal 5: Blast Radius (0-10) - CALCULATED FROM GRAPH
             CASE
                 WHEN n.blast_radius_count IS NOT NULL THEN CASE WHEN TOFLOAT(n.blast_radius_count) > 10 THEN 10 ELSE TOFLOAT(n.blast_radius_count) END
                 ELSE 0
             END as blast_score
        
        WITH n,
             cve_score + exploit_score + vector_score + exposure_score + blast_score as raw_score,
             cve_score, exploit_score, vector_score, exposure_score, blast_score
        
        WITH n,
             CASE WHEN raw_score > 100 THEN 100 ELSE raw_score END as final_score,
             cve_score, exploit_score, vector_score, exposure_score, blast_score
        
        SET n.risk_score = final_score,
            n.risk_score_updated_at = datetime()
        
        RETURN count(n) as updated_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                count = record.get("updated_count") if record else 0
            logger.info(f"Risk score calculation: Updated {count} nodes with formula")
            return count
        except Exception as e:
            logger.error(f"Risk score calculation failed: {str(e)}")
            return 0
    
    def _get_risk_statistics(self) -> Dict[str, Any]:
        """Get statistics about risk distribution"""
        query = """
        MATCH (n)
        WHERE n.risk_score IS NOT NULL
        WITH n.risk_score as risk
        RETURN 
          min(risk) as min_risk,
          max(risk) as max_risk,
          avg(risk) as avg_risk,
          count(*) as total_scored_nodes,
          count(CASE WHEN risk >= 80 THEN 1 END) as critical_count,
          count(CASE WHEN risk >= 60 AND risk < 80 THEN 1 END) as high_count,
          count(CASE WHEN risk >= 40 AND risk < 60 THEN 1 END) as medium_count,
          count(CASE WHEN risk < 40 THEN 1 END) as low_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                
                if record:
                    stats = {
                        "min_risk": round(float(record.get("min_risk") or 0), 2),
                        "max_risk": round(float(record.get("max_risk") or 0), 2),
                        "avg_risk": round(float(record.get("avg_risk") or 0), 2),
                        "total_scored_nodes": record.get("total_scored_nodes"),
                        "distribution": {
                            "critical (>=80)": record.get("critical_count"),
                            "high (60-79)": record.get("high_count"),
                            "medium (40-59)": record.get("medium_count"),
                            "low (<40)": record.get("low_count")
                        }
                    }
                    return stats
            return {}
        except Exception as e:
            logger.warning(f"Failed to get statistics: {str(e)}")
            return {}
    
    def get_highest_risk_nodes(self, limit: int = 10) -> list:
        """Get highest risk nodes"""
        query = """
        MATCH (n)
        WHERE n.risk_score IS NOT NULL
        RETURN {
            name: n.name,
            type: labels(n),
            risk_score: n.risk_score,
            incoming_relationships: n.incoming_relationship_count,
            blast_radius: n.blast_radius_count,
            cvss_score: n.cvss_score,
            compromised: n.compromised
        } as node_data
        ORDER BY n.risk_score DESC
        LIMIT $limit
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query, {"limit": limit})
                nodes = [record["node_data"] for record in result]
            return nodes
        except Exception as e:
            logger.error(f"Failed to get highest risk nodes: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.neo4j:
            self.neo4j.close()
            logger.info("Risk Calculator closed")


def run_risk_calculation(graph_name: str = DEFAULT_GRAPH) -> Dict[str, Any]:
    """Convenience function for command-line execution"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    calculator = RiskCalculator()
    try:
        result = calculator.recalculate_all_risk_scores(graph_name)
        
        # Print results
        print("\nRisk Calculation Result:")
        if result["status"] == "success":
            print(f"  Status: {result['status']}")
            print(f"  Exposure nodes: {result.get('exposure_nodes_updated', 0)}")
            print(f"  Blast radius nodes: {result.get('blast_radius_nodes_updated', 0)}")
            print(f"  Risk score nodes: {result.get('risk_score_nodes_updated', 0)}")
            
            stats = result.get("statistics", {})
            if stats:
                print(f"\nRisk Score Statistics:")
                print(f"  Total scored: {stats.get('total_scored_nodes')}")
                print(f"  Min risk: {stats.get('min_risk')}")
                print(f"  Max risk: {stats.get('max_risk')}")
                print(f"  Avg risk: {stats.get('avg_risk')}")
                
                dist = stats.get("distribution", {})
                print(f"\nDistribution:")
                for level, count in dist.items():
                    print(f"  {level}: {count}")
                
                print(f"\nTop Risk Nodes:")
                top_nodes = calculator.get_highest_risk_nodes(5)
                for i, node in enumerate(top_nodes, 1):
                    print(f"  {i}. {node.get('name', 'Unknown')} - Risk: {node.get('risk_score', 0)}")
        else:
            print(f"  Status: {result['status']}")
            print(f"  Error: {result.get('message')}")
        
        return result
    finally:
        calculator.close()


if __name__ == "__main__":
    import sys
    graph = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GRAPH
    run_risk_calculation(graph)
