"""
FastAPI Server for Caught U! Red Agent
Exposes Red Agent functionality via REST API endpoints
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from red_agent import RedAgent
from blue_agent import BlueAgent
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH, DEFAULT_GRAPH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Caught U! Red Agent API",
    description="Generative AI-powered attack vector analysis for banking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AttackVectorAnalysisRequest(BaseModel):
    """Request model for attack vector analysis"""
    graph: str = DEFAULT_GRAPH
    focus_server: Optional[str] = None

class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    services: Dict[str, str]

class RedAgentResponse(BaseModel):
    """Response model for Red Agent analysis"""
    status: str
    graph: str
    nodes_analyzed: int
    entries_enriched: int
    high_risk_nodes: List[Dict[str, Any]]
    attack_vectors: List[Dict[str, Any]]
    executive_summary: str
    defensive_priorities: List[str]
    blast_radii_summary: Dict[str, Any]
    neo4j_relationships: List[Dict[str, Any]]
    timestamp: str


# Global Red Agent instance
red_agent = None
blue_agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize Red Agent and Blue Agent on startup"""
    global red_agent, blue_agent
    try:
        red_agent = RedAgent()
        blue_agent = BlueAgent()
        logger.info("Red Agent and Blue Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agents: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global red_agent, blue_agent
    if red_agent and hasattr(red_agent, 'neo4j'):
        # Close Neo4j connection if it has a close method
        if hasattr(red_agent.neo4j, 'close'):
            red_agent.neo4j.close()
        logger.info("Red Agent closed")
    
    if blue_agent and hasattr(blue_agent, 'neo4j'):
        if hasattr(blue_agent.neo4j, 'close'):
            blue_agent.neo4j.close()
        logger.info("Blue Agent closed")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    Verifies that all services (Neo4j, Gemini) are accessible
    """
    try:
        # Check if red agent is initialized
        if not red_agent:
            neo4j_status = "✗ Not Initialized"
            llm_status = "✗ Not Initialized"
        else:
            # Check Neo4j connection
            neo4j_status = "✓ Connected" if red_agent.neo4j.check_connection() else "✗ Failed"
            
            # Check LLM client
            llm_status = "✓ Ready" if red_agent.llm else "✗ Failed"
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            services={
                "neo4j": neo4j_status,
                "gemini_llm": llm_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/red-agent/analyze")
async def analyze_attack_vectors(request: AttackVectorAnalysisRequest):
    """
    Analyze attack vectors for specified graph
    
    Flow:
    1. Fetch server nodes from Neo4j (product, version, IP, criticality)
    2. Get CVE data from NVD for those products
    3. Merge data and prioritize using Gemini LLM
    4. Return structured attack vector analysis
    
    Args:
        request: Analysis request with graph name and optional focus server
    
    Returns:
        Structured attack vector analysis
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        # Validate graph name
        if request.graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid graph: {request.graph}. Must be '{PRODUCTION_GRAPH}' or '{SIMULATION_GRAPH}'"
            )
        
        logger.info(f"Starting attack vector analysis on {request.graph} graph")
        
        # Run analysis
        result = red_agent.analyze_attack_vectors(
            graph_name=request.graph,
            focus_server=request.focus_server
        )
        
        # Add timestamp
        result['timestamp'] = datetime.now().isoformat()
        
        # Handle errors
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('message', 'Analysis failed'))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Attack vector analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analyze-attack-vectors")
async def analyze_attack_vectors_get(graph: str = DEFAULT_GRAPH, focus_server: Optional[str] = None):
    """
    Analyze attack vectors for specified graph (GET endpoint)
    
    Args:
        graph: Graph name ("prod" or "sim") - defaults to prod
        focus_server: Optional specific node to focus on
    
    Returns:
        Dynamic attack analysis with Gemini-generated insights
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        # Validate graph name
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid graph: {graph}. Must be '{PRODUCTION_GRAPH}' or '{SIMULATION_GRAPH}'"
            )
        
        logger.info(f"Starting dynamic attack vector analysis on {graph} graph")
        
        # Run analysis
        result = red_agent.analyze_attack_vectors(
            graph_name=graph,
            focus_server=focus_server
        )
        
        # Add timestamp
        result['timestamp'] = datetime.now().isoformat()
        
        # Handle errors
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('message', 'Analysis failed'))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Attack vector analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/red-agent/servers/{graph}")
async def get_servers(graph: str = DEFAULT_GRAPH):
    """
    Get all servers from specified graph
    
    Args:
        graph: Graph name ("prod" or "sim")
    
    Returns:
        List of server nodes
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        servers = red_agent.neo4j.get_servers(graph_name=graph)
        
        return {
            "status": "success",
            "graph": graph,
            "servers_count": len(servers),
            "servers": servers,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch servers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/red-agent/vulnerabilities/{graph}")
async def get_vulnerabilities(graph: str = PRODUCTION_GRAPH):
    """
    Get all vulnerabilities for servers in specified graph
    
    Args:
        graph: Graph name ("prod" or "sim")
    
    Returns:
        List of vulnerabilities
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        servers = red_agent.neo4j.get_servers(graph_name=graph)
        vulnerabilities = red_agent.neo4j.get_vulnerabilities_for_servers(servers)
        
        return {
            "status": "success",
            "graph": graph,
            "vulnerabilities_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch vulnerabilities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/red-agent/blast-radius/{graph}/{server_name}")
async def get_blast_radius(graph: str, server_name: str):
    """
    Calculate blast radius for a specific server
    Shows all nodes that could be affected if this server is compromised
    
    Args:
        graph: Graph name ("prod" or "sim")
        server_name: Name of the server
    
    Returns:
        List of affected nodes
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        blast_radius = red_agent.neo4j.get_blast_radius(server_name, graph_name=graph)
        
        return {
            "status": "success",
            "server_name": server_name,
            "graph": graph,
            "affected_nodes_count": len(blast_radius),
            "affected_nodes": blast_radius,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to calculate blast radius: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/red-agent/high-criticality-servers/{graph}")
async def get_high_criticality_servers(graph: str = PRODUCTION_GRAPH):
    """
    Get high and critical criticality servers
    
    Args:
        graph: Graph name ("prod" or "sim")
    
    Returns:
        List of high-risk servers
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        servers = red_agent.neo4j.get_high_criticality_servers(graph_name=graph)
        
        return {
            "status": "success",
            "graph": graph,
            "high_criticality_count": len(servers),
            "servers": servers,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch high-criticality servers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/red-agent/cves/{product}")
async def get_cves_for_product(product: str):
    """
    Get CVEs for a specific product from NVD cache
    Note: CVE data is synced via nvd_sync.py script and stored in Neo4j nodes
    
    Args:
        product: Product name (e.g., "openssh", "openssl")
    
    Returns:
        List of nodes with CVE data
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        # Query Neo4j for nodes with CVE data for this product
        with red_agent.neo4j.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.product_mapped = $product AND n.cve_id IS NOT NULL
                RETURN n.name, n.cvss_score, n.cve_id, n.exploit_available, n.attack_vector
                ORDER BY n.cvss_score DESC
            """, {"product": product})
            
            cves = [dict(record) for record in result]
        
        return {
            "status": "success",
            "product": product,
            "cves_count": len(cves),
            "cves": cves,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch CVEs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/red-agent/products")
async def get_all_products():
    """
    Get all NVD products and the banking nodes mapped to them
    Shows product-to-node mappings from nvd_sync enrichment
    
    Returns:
        Dictionary of products with mapped nodes
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        # Query Neo4j for all distinct products with their nodes
        with red_agent.neo4j.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.product_mapped IS NOT NULL
                RETURN DISTINCT n.product_mapped as product,
                       collect({
                           name: n.name,
                           type: n.type,
                           risk_score: n.risk_score,
                           cvss_score: n.cvss_score,
                           cve_id: n.cve_id
                       }) as nodes
                ORDER BY product
            """)
            
            products = {}
            for record in result:
                product = record.get("product")
                nodes = record.get("nodes")
                if product:
                    products[product] = nodes
        
        return {
            "status": "success",
            "products_count": len(products),
            "products": products,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/red-agent/remediation-playbook")
async def generate_remediation_playbook(attack_vector: Dict[str, Any], server_properties: Dict[str, Any]):
    """
    Generate a remediation playbook for a specific attack vector
    
    Args:
        attack_vector: The attack vector to remediate
        server_properties: Properties of the affected server
    
    Returns:
        Step-by-step remediation instructions
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        playbook = red_agent.llm.generate_remediation_playbook(
            attack_vector=attack_vector,
            server_properties=server_properties
        )
        
        return {
            "status": "success",
            "playbook": playbook,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to generate playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Blue Agent Endpoints
@app.post("/api/blue-agent/remediation-playbook")
async def blue_agent_generate_playbook(attack_vector: Dict[str, Any], server_properties: Dict[str, Any], risk_context: Optional[Dict[str, Any]] = None):
    """
    Blue Agent: Generate remediation playbook with risk-aware severity levels
    
    Args:
        attack_vector: The attack vector to remediate
        server_properties: Properties of the affected server (including risk_score)
        risk_context: Optional risk context (blast_radius_count, etc.)
    
    Returns:
        Risk-aware remediation playbook with severity level
    """
    try:
        if not blue_agent:
            raise HTTPException(status_code=503, detail="Blue Agent not initialized")
        
        playbook = blue_agent.generate_playbook(
            attack_vector=attack_vector,
            server_properties=server_properties,
            risk_context=risk_context
        )
        
        return {
            "status": "success",
            "playbook": playbook,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to generate blue agent playbook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/blue-agent/isolate/{graph}/{server_name}")
async def blue_agent_isolate_node(graph: str, server_name: str):
    """
    Blue Agent: Isolate a compromised node by removing all its edges
    Prevents the node from affecting other systems
    
    Args:
        graph: Graph name ("prod" or "sim")
        server_name: Name of the server to isolate
    
    Returns:
        Isolation result with edges deleted and risk scores
    """
    try:
        if not blue_agent:
            raise HTTPException(status_code=503, detail="Blue Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        result = blue_agent.apply_fix(server_name=server_name, graph_name=graph)
        
        return {
            "status": "success",
            "isolation_result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to isolate node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blue-agent/threats/{graph}")
async def blue_agent_analyze_threats(graph: str = PRODUCTION_GRAPH):
    """
    Blue Agent: Analyze threats - identify high-risk nodes requiring remediation
    Returns prioritized list of threats with severity levels based on risk scores
    
    Args:
        graph: Graph name ("prod" or "sim")
    
    Returns:
        Prioritized threats with risk scores and severity levels
    """
    try:
        if not blue_agent:
            raise HTTPException(status_code=503, detail="Blue Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        result = blue_agent.analyze_threats(graph_name=graph)
        
        return {
            "status": result.get("status"),
            "graph": graph,
            "threats_count": result.get("threats_count", 0),
            "threats": result.get("threats", []),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to analyze threats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/blue-agent/isolation-impact/{graph}/{server_name}")
async def blue_agent_isolation_impact(graph: str, server_name: str):
    """
    Blue Agent: Analyze impact of isolating a specific node
    Shows how many nodes depend on this server and risk reduction
    
    Args:
        graph: Graph name ("prod" or "sim")
        server_name: Name of the server to analyze
    
    Returns:
        Impact analysis with affected nodes and risk reduction estimate
    """
    try:
        if not blue_agent:
            raise HTTPException(status_code=503, detail="Blue Agent not initialized")
        
        if graph not in [PRODUCTION_GRAPH, SIMULATION_GRAPH]:
            raise HTTPException(status_code=400, detail=f"Invalid graph: {graph}")
        
        result = blue_agent.get_isolation_impact(server_name=server_name, graph_name=graph)
        
        return {
            "status": result.get("status"),
            "server_name": server_name,
            "graph": graph,
            "current_risk_score": result.get("current_risk_score"),
            "severity_level": result.get("severity_level"),
            "affected_nodes_count": result.get("affected_nodes_count", 0),
            "isolation_recommended": result.get("isolation_recommended", False),
            "affected_nodes": result.get("affected_nodes", []),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to analyze isolation impact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "project": "Caught U!",
        "version": "1.0.0",
        "description": "Generative AI-powered cybersecurity platform for banking",
        "red_agent_endpoints": {
            "analyze_attack_vectors_get": "GET /analyze-attack-vectors?graph=prod",
            "analyze_attack_vectors_post": "POST /api/red-agent/analyze",
            "get_servers": "GET /api/red-agent/servers/{graph}",
            "get_vulnerabilities": "GET /api/red-agent/vulnerabilities/{graph}",
            "get_blast_radius": "GET /api/red-agent/blast-radius/{graph}/{server_name}",
            "get_high_criticality_servers": "GET /api/red-agent/high-criticality-servers/{graph}",
            "get_products": "GET /api/red-agent/products",
            "get_cves": "GET /api/red-agent/cves/{product}",
            "red_agent_playbook": "POST /api/red-agent/remediation-playbook"
        },
        "blue_agent_endpoints": {
            "analyze_threats": "GET /api/blue-agent/threats/{graph}",
            "isolation_impact": "GET /api/blue-agent/isolation-impact/{graph}/{server_name}",
            "blue_agent_playbook": "POST /api/blue-agent/remediation-playbook",
            "blue_agent_isolate": "POST /api/blue-agent/isolate/{graph}/{server_name}"
        },
        "utility_endpoints": {
            "health": "GET /health"
        },
        "documentation": "/docs"
    }



if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
