import logging
import hmac
import hashlib
from fastapi import FastAPI, HTTPException, status, Request
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

def verify_shopify_proxy_signature(request: Request) -> bool:
    """
    Calculates the Shopify App Proxy signature and compares it with the incoming query parameter.
    Returns True if signature is valid, False otherwise.
    """
    secret = settings.SHOPIFY_API_SECRET
    if not secret:
        logger.error("Shopify App Proxy verification skipped: SHOPIFY_API_SECRET is not set.")
        return False

    params = dict(request.query_params)
    signature = params.pop("signature", None)
    if not signature:
        logger.warning("Shopify App Proxy verification failed: Missing signature parameter.")
        return False

    sorted_keys = sorted(params.keys())
    data_parts = []
    for key in sorted_keys:
        value = params[key]
        if isinstance(value, list):
            data_parts.append(f"{key}={','.join(value)}")
        else:
            data_parts.append(f"{key}={value}")

    data_string = "".join(data_parts)
    
    computed_signature = hmac.new(
        secret.encode("utf-8"),
        data_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, signature)

@app.get("/api/v1/pricing/verify-proxy", tags=["Pricing Engine"])
async def verify_proxy_route(request: Request):
    """
    Dedicated testing route to verify that the App Proxy signature validation is working.
    """
    if verify_shopify_proxy_signature(request):
        return {"status": "verified"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid signature or verification failed."
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
async def calculate_pricing(payload: PricingRequest, request: Request):
    """
    Calculates regional custom price rules for a given product and ZIP code.
    If no regional rule is mapped, returns a fallback code signaling standard Shopify pricing.
    """
    logger.info(f"[{payload.request_id}] Querying dynamic pricing for product_id={payload.product_id}, zip_code='{payload.zip_code}'")
    
    # Dry-Run Signature check (log status only, do not enforce or block)
    if "signature" in request.query_params:
        if verify_shopify_proxy_signature(request):
            logger.info(f"[{payload.request_id}] Shopify App Proxy signature verified successfully.")
        else:
            logger.warning(f"[{payload.request_id}] Shopify App Proxy signature verification FAILED.")
    else:
        logger.info(f"[{payload.request_id}] Direct storefront API call received (no signature).")
    
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
