from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.deps import require_admin
from src.database.database import get_db
from src.services.dashboard import get_dashboard_metrics

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    return get_dashboard_metrics(db)
