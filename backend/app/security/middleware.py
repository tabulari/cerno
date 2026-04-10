import time
import structlog
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.redis import get_redis
from app.config import get_settings

logger = structlog.get_logger()

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/v1/incidents") or request.method != "POST":
            return await call_next(request)

        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        
        try:
            redis = await get_redis()
            
            # Simple token bucket / counter for IP-based rate limiting (30 RPM)
            ip_key = f"rate_limit:ip:{client_ip}"
            ip_count = await redis.incr(ip_key)
            if ip_count == 1:
                await redis.expire(ip_key, 60)
            
            if ip_count > settings.rate_limit_rpm:
                logger.warning("security.rate_limit.ip_exceeded", ip=client_ip)
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests from this IP")

            # Check user submission limits if authenticated
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # We'll rely on the route's auth dependency for actual validation, 
                # but we can try to decode token payload here or just use token hash as key
                import hashlib
                token_hash = hashlib.sha256(auth_header.encode()).hexdigest()
                user_key = f"rate_limit:user:{token_hash}"
                user_count = await redis.incr(user_key)
                if user_count == 1:
                    await redis.expire(user_key, 3600)  # 1 hour
                
                if user_count > settings.rate_limit_submissions_per_hour:
                    logger.warning("security.rate_limit.user_exceeded", token_hash=token_hash[:8])
                    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Submission limit exceeded for user")

        except HTTPException:
            raise
        except Exception as e:
            logger.error("security.rate_limit.error", error=str(e))
            # Fail open if Redis is down
            pass

        return await call_next(request)
