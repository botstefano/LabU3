
from typing import List
from uuid import UUID
import joblib
import io
import logging

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User, UserRole
from app.routers.deps import get_current_user, require_roles
from app.schemas.risk import ClientRiskResponse, TrainRiskResponse, TrainingStatus, CompareModelsResponse, TrainModelWithTypeRequest
from app.services.risk_service import RiskService
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/risk", tags=["Riesgo de Morosidad (IA)"])


@router.post("/upload-model")
def upload_trained_model(
    file: UploadFile = File(...)
):
    """Receive trained model from Streamlit and save it for backend use"""
    logger.info("[BACKEND] Upload model endpoint called")
    try:
        # Read the model file
        model_data = file.file.read()
        logger.info(f"[BACKEND] Received model file, size: {len(model_data)} bytes")
        
        # Save to backend model path
        model_path = Path(__file__).parent.parent / "ml" / "model_artifacts" / "risk_model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"[BACKEND] Target path: {model_path}")
        logger.info(f"[BACKEND] Path exists before: {model_path.exists()}")
        
        # Load and save the model
        model = joblib.load(io.BytesIO(model_data))
        joblib.dump(model, model_path)
        
        logger.info(f"[BACKEND] Model saved successfully")
        logger.info(f"[BACKEND] Path exists after: {model_path.exists()}")
        logger.info(f"[BACKEND] File size: {model_path.stat().st_size if model_path.exists() else 0} bytes")
        
        return {"message": "Model uploaded successfully", "path": str(model_path)}
    except Exception as e:
        import traceback
        logger.error(f"[BACKEND] Error uploading model: {str(e)}")
        logger.error(f"[BACKEND] Traceback: {traceback.format_exc()}")
        return {"error": str(e)}, 400


@router.post("/train", response_model=TrainRiskResponse)
def train_model(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    return RiskService(db).train()


@router.post("/upload-dataset", response_model=TrainRiskResponse)
def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    service = RiskService(db)
    
    content = file.file.read().decode('utf-8')
    
    if file.filename.endswith('.csv'):
        dataset = service.parse_dataset_from_csv(content)
    elif file.filename.endswith('.json'):
        dataset = service.parse_dataset_from_json(content)
    else:
        raise ValueError("Formato no soportado. Use CSV o JSON.")
    
    return service.train_with_dataset(dataset)


@router.get("/training-status", response_model=TrainingStatus)
def get_training_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).get_training_status()


@router.get("/clients", response_model=List[ClientRiskResponse])
def list_clients_risk(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).score_all_clients()


@router.get("/clients/{client_id}", response_model=ClientRiskResponse)
def get_client_risk(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).score_client(client_id)


@router.post("/compare-models", response_model=CompareModelsResponse)
def compare_models(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    return RiskService(db).compare_models()


@router.post("/train-with-type", response_model=TrainRiskResponse)
def train_model_with_type(
    request: TrainModelWithTypeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRADOR, UserRole.CONTADOR)),
):
    return RiskService(db).train_with_type(request.model_type)


@router.get("/collection-priority")
def get_collection_priority(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).listar_clientes_para_cobranza()


@router.get("/credit-limit/{client_id}")
def get_credit_limit_suggestion(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return RiskService(db).sugerir_limite_credito(str(client_id))

