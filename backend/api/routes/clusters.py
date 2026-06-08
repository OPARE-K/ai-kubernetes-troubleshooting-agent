from fastapi import APIRouter, HTTPException

from kubernetes.clusters import check_cluster_health, kubeconfig_status, list_clusters

router = APIRouter(tags=["clusters"])


@router.get("/clusters")
def get_clusters() -> dict:
    return list_clusters()


@router.get("/clusters/{context}/health")
def get_cluster_health(context: str) -> dict:
    status = kubeconfig_status()
    if not status["configured"]:
        raise HTTPException(status_code=503, detail=status["message"])
    return check_cluster_health(context)
