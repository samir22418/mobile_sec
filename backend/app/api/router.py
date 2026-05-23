from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.telemetry import router as telemetry_router
from app.api.devices import router as devices_router
from app.api.payloads import router as payloads_router
from app.api.feedback import router as feedback_router
from app.api.enrollment_tokens import router as enrollment_tokens_router
from app.api.admin_ui import router as admin_ui_router

router = APIRouter()

router.include_router(admin_ui_router)
router.include_router(health_router)
router.include_router(telemetry_router)
router.include_router(devices_router)
router.include_router(payloads_router)
router.include_router(feedback_router)
router.include_router(enrollment_tokens_router)
