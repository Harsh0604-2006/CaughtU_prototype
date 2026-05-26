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
from config import PRODUCTION_GRAPH, SIMULATION_GRAPH

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
    graph: str = PRODUCTION_GRAPH
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


@app.on_event("startup")
async def startup_event():
    """Initialize Red Agent on startup"""
    global red_agent
    try:
        red_agent = RedAgent()
        logger.info("Red Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Red Agent: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global red_agent
    if red_agent:
        red_agent.close()
        logger.info("Red Agent closed")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    Verifies that all services (Neo4j, Gemini, NVD) are accessible
    """
    try:
        # Check Neo4j connection
        neo4j_status = "✓ Connected" if red_agent.neo4j.check_connection() else "✗ Failed"
        
        # Check NVD client
        nvd_status = "✓ Ready" if red_agent.nvd else "✗ Failed"
        
        # Check LLM client
        llm_status = "✓ Ready" if red_agent.llm else "✗ Failed"
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            services={
                "neo4j": neo4j_status,
                "nvd": nvd_status,
                "gemini_llm": llm_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/red-agent/analyze", response_model=RedAgentResponse)
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


@app.get("/api/red-agent/servers/{graph}")
async def get_servers(graph: str = PRODUCTION_GRAPH):
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
    
    Args:
        product: Product name (e.g., "openssh", "openssl")
    
    Returns:
        List of CVEs for the product
    """
    try:
        if not red_agent:
            raise HTTPException(status_code=503, detail="Red Agent not initialized")
        
        cves = red_agent.nvd.get_cves_for_product(product)
        
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


@app.get("/")
async def root():
    """Root endpoint with API documentation"""
    return {
        "project": "Caught U!",
        "version": "1.0.0",
        "description": "Generative AI-powered cybersecurity platform for banking",
        "endpoints": {
            "health": "GET /health",
            "analyze_attack_vectors": "POST /api/red-agent/analyze",
            "get_servers": "GET /api/red-agent/servers/{graph}",
            "get_vulnerabilities": "GET /api/red-agent/vulnerabilities/{graph}",
            "get_blast_radius": "GET /api/red-agent/blast-radius/{graph}/{server_name}",
            "get_high_criticality_servers": "GET /api/red-agent/high-criticality-servers/{graph}",
            "get_cves": "GET /api/red-agent/cves/{product}",
            "generate_playbook": "POST /api/red-agent/remediation-playbook"
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
