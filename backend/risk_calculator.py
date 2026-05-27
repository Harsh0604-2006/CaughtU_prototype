"""
Risk Calculator Module
Calculates dynamic risk scores from real signals in Neo4j
Reads CVE data + graph topology
Writes blast_radius_count and risk_score to nodes
This is Step 2 of the dynamic risk scoring pipeline
"""
import logging
from typing import Dict, Any
from neo4j_client import Neo4jClient
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH

logger = logging.getLogger(__name__)


class RiskCalculator:
    """
    Calculate risk scores dynamically from real signals:
    - CVE data (cvss_score, exploit_available, attack_vector)
    - Graph topology (connections, critical downstream nodes)
    - Node properties (type, status, compromised)
    """
    
    def __init__(self):
        """Initialize risk calculator"""
        self.neo4j = Neo4jClient()
    
    def recalculate_all_risk_scores(self, graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
        """
        Main method - recalculate risk scores for all nodes
        
        Args:
            graph_name: "prod" or "sim"
        
        Returns:
            Calculation results with counts
        """
        logger.info(f"Starting risk score recalculation for {graph_name} graph")
        
        try:
            # Step 1: Calculate blast radius for each node
            logger.info("Step 1: Calculating blast_radius_count for each node")
            blast_nodes = self._calculate_blast_radius_scores()
            
            logger.info(f"Updated blast radius scores for {blast_nodes} nodes")
            
            # Step 2: Calculate final risk scores from formula
            logger.info("Step 2: Calculating final risk_score from formula")
            risk_nodes = self._calculate_risk_scores()
            
            logger.info(f"Updated risk scores for {risk_nodes} nodes")
            
            # Step 3: Get statistics
            logger.info("Step 3: Gathering statistics")
            stats = self._get_risk_statistics()
            
            result = {
                "status": "success",
                "graph": graph_name,
                "blast_radius_nodes_updated": blast_nodes,
                "risk_score_nodes_updated": risk_nodes,
                "statistics": stats
            }
            
            logger.info(f"Risk score calculation complete")
            return result
        
        except Exception as e:
            logger.error(f"Risk calculation failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "blast_radius_nodes_updated": 0,
                "risk_score_nodes_updated": 0
            }
    
    def _calculate_blast_radius_scores(self) -> int:
        """
        Calculate how many critical/important nodes each node can reach
        
        Query: For each node, count downstream nodes with critical types
        (Database, Payment, Finance, Core systems)
        
        Returns:
            Number of nodes updated
        """
        query = """
        MATCH (n)
        WHERE n:Server OR n:NetworkNode OR n:Device OR n:API
        OPTIONAL MATCH (n)-[:CONNECTS_TO|ROUTES_TO|RELAYS_TO*1..4]->(target)
        WHERE target.type IN ["Database", "Payment", "Finance", "Core", "Critical"]
        WITH n, count(DISTINCT target) as downstream_critical
        SET n.blast_radius_count = downstream_critical
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
            return 0
    
    def _calculate_risk_scores(self) -> int:
        """
        Calculate final risk score from formula:
        
        risk_score = cve_component + exploit_component + vector_component + blast_component
        
        Where:
        - cve_component = cvss_score * 4 (0-40 points, max cvss 10.0)
        - exploit_component = 20 if exploit_available, else 0
        - vector_component = 20 if attack_vector = Network, else 0
        - blast_component = based on downstream critical nodes (0-20 points)
        
        Total: 0-100 points
        
        Returns:
            Number of nodes updated
        """
        query = """
        MATCH (n)
        WHERE n:Server OR n:NetworkNode OR n:Device OR n:API
        WITH n,
          // CVE component: 0-40 points
          (CASE WHEN n.cvss_score IS NOT NULL 
                THEN toFloat(n.cvss_score) * 4 
                ELSE 0 
           END) as cve_component,
          
          // Exploit availability: 0-20 points
          (CASE WHEN n.exploit_available = "true" 
                THEN 20 
                ELSE 0 
           END) as exploit_component,
          
          // Network attack vector: 0-20 points
          (CASE WHEN n.attack_vector = "Network" OR n.attack_vector = "NETWORK"
                THEN 20 
                ELSE 0 
           END) as vector_component,
          
          // Blast radius component: 0-20 points
          // based on how many critical downstream nodes exist
          (CASE WHEN (n.blast_radius_count IS NULL OR n.blast_radius_count = 0)
                THEN 5
                WHEN n.blast_radius_count > 10
                THEN 20
                WHEN n.blast_radius_count > 5
                THEN 15
                WHEN n.blast_radius_count > 3
                THEN 10
                ELSE 5
           END) as blast_component
        
        // Additional boost for already compromised nodes
        WITH n, cve_component, exploit_component, vector_component, blast_component,
             (CASE WHEN n.compromised = true 
                   THEN 10
                   ELSE 0
              END) as compromised_boost
        
        // Additional boost for high-value node types
        WITH n, cve_component, exploit_component, vector_component, blast_component, compromised_boost,
             (CASE WHEN n.type IN ["Payment", "Database", "Finance", "Core"]
                   THEN 5
                   ELSE 0
              END) as type_boost
        
        // Calculate final score (capped at 100)
        WITH n, 
             cve_component + exploit_component + vector_component + blast_component + compromised_boost + type_boost as raw_score
        
        SET n.risk_score = CASE WHEN raw_score > 100 THEN 100 ELSE raw_score END,
            n.risk_score_updated_at = datetime()
        
        RETURN count(n) as updated_count
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query)
                record = result.single()
                count = record.get("updated_count") if record else 0
            
            logger.info(f"Risk score calculation: Updated {count} nodes")
            return count
        
        except Exception as e:
            logger.error(f"Risk score calculation failed: {str(e)}")
            return 0
    
    def _get_risk_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about risk scores in the graph
        
        Returns:
            Dictionary with min, max, avg risk scores and distribution
        """
        query = """
        MATCH (n)
        WHERE n.risk_score IS NOT NULL
        WITH n.risk_score as risk
        RETURN 
          min(risk) as min_risk,
          max(risk) as max_risk,
          avg(risk) as avg_risk,
          count(*) as total_scored_nodes,
          
          // Risk distribution
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
                        "min_risk": record.get("min_risk"),
                        "max_risk": record.get("max_risk"),
                        "avg_risk": round(record.get("avg_risk", 0), 2),
                        "total_scored_nodes": record.get("total_scored_nodes"),
                        "distribution": {
                            "critical": record.get("critical_count"),  # >= 80
                            "high": record.get("high_count"),          # 60-79
                            "medium": record.get("medium_count"),      # 40-59
                            "low": record.get("low_count")             # < 40
                        }
                    }
                    return stats
                
            return {}
        
        except Exception as e:
            logger.warning(f"Failed to get statistics: {str(e)}")
            return {}
    
    def get_highest_risk_nodes(self, limit: int = 10) -> list:
        """
        Get nodes with highest risk scores
        
        Args:
            limit: Number of nodes to return
        
        Returns:
            List of nodes sorted by risk score descending
        """
        query = """
        MATCH (n)
        WHERE n.risk_score IS NOT NULL
        RETURN n.name as name,
               n.type as type,
               n.risk_score as risk_score,
               n.cvss_score as cvss_score,
               n.blast_radius_count as blast_radius,
               n.exploit_available as exploit_available
        ORDER BY n.risk_score DESC
        LIMIT $limit
        """
        
        try:
            with self.neo4j.driver.session() as session:
                result = session.run(query, {"limit": limit})
                nodes = [dict(record) for record in result]
            
            return nodes
        
        except Exception as e:
            logger.error(f"Failed to get highest risk nodes: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        self.neo4j.close()
        logger.info("Risk Calculator closed")


def run_risk_calculation(graph_name: str = PRODUCTION_GRAPH) -> Dict[str, Any]:
    """
    Convenience function to run risk score calculation
    
    Args:
        graph_name: "prod" or "sim"
    
    Returns:
        Calculation results
    """
    calculator = RiskCalculator()
    try:
        result = calculator.recalculate_all_risk_scores(graph_name=graph_name)
        
        # Also get high-risk nodes for reference
        high_risk = calculator.get_highest_risk_nodes(limit=5)
        result["top_risk_nodes"] = high_risk
        
        return result
    finally:
        calculator.close()


if __name__ == "__main__":
    import sys
    import json
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run calculation on specified graph
    graph = sys.argv[1] if len(sys.argv) > 1 else PRODUCTION_GRAPH
    logger.info(f"Running risk score calculation on {graph} graph")
    
    result = run_risk_calculation(graph_name=graph)
    
    print(f"\nRisk Calculation Result:")
    print(f"  Status: {result['status']}")
    print(f"  Blast radius nodes: {result['blast_radius_nodes_updated']}")
    print(f"  Risk score nodes: {result['risk_score_nodes_updated']}")
    
    if result.get('statistics'):
        stats = result['statistics']
        print(f"\nRisk Score Statistics:")
        print(f"  Total scored: {stats.get('total_scored_nodes')}")
        print(f"  Min risk: {stats.get('min_risk')}")
        print(f"  Max risk: {stats.get('max_risk')}")
        print(f"  Avg risk: {stats.get('avg_risk')}")
        
        dist = stats.get('distribution', {})
        print(f"\nDistribution:")
        print(f"  Critical (80+): {dist.get('critical')}")
        print(f"  High (60-79): {dist.get('high')}")
        print(f"  Medium (40-59): {dist.get('medium')}")
        print(f"  Low (<40): {dist.get('low')}")
    
    if result.get('top_risk_nodes'):
        print(f"\nTop Risk Nodes:")
        for i, node in enumerate(result['top_risk_nodes'][:5], 1):
            print(f"  {i}. {node.get('name')} - Risk: {node.get('risk_score')} "
                  f"(CVSS: {node.get('cvss_score')}, Blast: {node.get('blast_radius')})")
    
    if result.get('message'):
        print(f"\nError: {result['message']}")
