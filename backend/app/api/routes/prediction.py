from fastapi import APIRouter

from app.schemas.prediction import (
    JobPostingRequest,
    PredictionResponse
)

from app.ml.model_service import predict_job

router = APIRouter(
    prefix="/predict",
    tags=["Prediction"]
)

@router.post(
    "",
    response_model=PredictionResponse
)
def predict(
    job : JobPostingRequest
):
    result = predict_job(
        job.model_dump()
    )
    return result