import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.schemas import PricingRequest, PricingResponse
from app.services import PricingService

from fastapi.encoders import jsonable_encoder

# Configure logging for observability and production visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pricing-api")

# Initialize app with metadata for recruiter-friendly interactive docs (/docs)
app = FastAPI(
    title="Shopify Dynamic Pricing API",
    description="Microservice providing location-aware product pricing adjustments based on customer ZIP codes.",
    version="1.0.0"
)

# Mount CORS Middleware to authorize secure cross-origin requests from Shopify storefronts
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Custom exception handler to log validation errors and return structured client responses.
    """
    errors = exc.errors()
    logger.warning(f"Validation failed for request: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(errors)}
    )

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Operational"])
async def health_check():
    """
    Liveness and Readiness probe endpoint for Render container orchestration and uptime monitors.
    """
    return {"status": "healthy"}

@app.post(
    "/api/v1/pricing/calculate", 
    response_model=PricingResponse, 
    status_code=status.HTTP_200_OK, 
    tags=["Pricing Engine"]
)
async def calculate_pricing(payload: PricingRequest):
    """
    Calculates regional custom price rules for a given product and ZIP code.
    If no regional rule is mapped, returns a fallback code signaling standard Shopify pricing.
    """
    logger.info(f"[{payload.request_id}] Querying dynamic pricing for product_id={payload.product_id}, zip_code='{payload.zip_code}'")
    
    try:
        custom_price = await PricingService.get_price(
            product_id=payload.product_id, 
            zip_code=payload.zip_code
        )
        
        if custom_price is not None:
            formatted = PricingService.format_currency(custom_price)
            logger.info(f"[{payload.request_id}] Custom price applied: {formatted} for ZIP {payload.zip_code}")
            return PricingResponse(
                success=True,
                zip_code=payload.zip_code,
                product_id=payload.product_id,
                price=custom_price,
                formatted_price=formatted,
                is_custom=True,
                message="Custom regional price successfully matched."
            )
            
        logger.info(f"[{payload.request_id}] No pricing rules match for ZIP {payload.zip_code}. Standard pricing applies.")
        return PricingResponse(
            success=True,
            zip_code=payload.zip_code,
            product_id=payload.product_id,
            price=None,
            formatted_price=None,
            is_custom=False,
            message="No pricing rule exists for this ZIP code. Default storefront prices apply."
        )

    except Exception as e:
        logger.error(f"[{payload.request_id}] Unexpected internal pricing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating dynamic pricing."
        )
