"""
Security Module for SceneIQ
Provides input validation, rate limiting, and security headers
"""

import re
from typing import Any, Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validates user inputs for common security threats"""
    
    # SQL injection patterns - check for suspicious keywords
    SQL_KEYWORDS = [
        "UNION", "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
        "ALTER", "EXEC", "EXECUTE", "OR", "AND"
    ]
    
    # Script injection patterns
    SCRIPT_PATTERNS = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"onclick=",
    ]
    
    @staticmethod
    def is_sql_injection(value: str) -> bool:
        """Check if value contains SQL injection patterns"""
        if not isinstance(value, str):
            return False
        
        # Check for SQL keywords
        value_upper = value.upper()
        for keyword in SecurityValidator.SQL_KEYWORDS:
            if keyword in value_upper:
                # Check if it looks suspicious (e.g., "OR '1'='1")
                if keyword == "OR" and "=" in value:
                    return True
                elif keyword in ["SELECT", "UNION", "INSERT", "DELETE", "DROP"]:
                    return True
        
        # Check for SQL comment syntax
        if "--" in value or "/*" in value or "*/" in value:
            return True
        
        return False
    
    @staticmethod
    def is_script_injection(value: str) -> bool:
        """Check if value contains script injection patterns"""
        if not isinstance(value, str):
            return False
        
        for pattern in SecurityValidator.SCRIPT_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def is_command_injection(value: str) -> bool:
        """Check if value contains command injection patterns"""
        if not isinstance(value, str):
            return False
        
        # Check for pipe operator
        if "|" in value and "grep" in value:
            return True
        
        # Check for command chaining
        if "&&" in value or "||" in value:
            return True
        
        # Check for common dangerous commands at start or after operators
        dangerous_cmds = ["wget", "curl", "cat", "ls", "rm", "bash", "sh"]
        for cmd in dangerous_cmds:
            if re.search(rf'\b{cmd}\b', value, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def validate_input(value: Any, field_name: str = "input") -> None:
        """
        Validate input for common security threats
        
        Raises:
            HTTPException: If input contains suspicious patterns
        """
        if not isinstance(value, str):
            return
        
        if SecurityValidator.is_sql_injection(value):
            logger.warning(f"SQL injection attempt detected in {field_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters in {field_name}"
            )
        
        if SecurityValidator.is_script_injection(value):
            logger.warning(f"Script injection attempt detected in {field_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters in {field_name}"
            )
        
        if SecurityValidator.is_command_injection(value):
            logger.warning(f"Command injection attempt detected in {field_name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid characters in {field_name}"
            )


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # {ip: [(timestamp, count), ...]}
    
    def is_rate_limited(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit"""
        now = datetime.utcnow()
        window = now - timedelta(minutes=1)
        
        if ip not in self.requests:
            self.requests[ip] = [(now, 1)]
            return False
        
        # Remove old requests outside the window
        self.requests[ip] = [
            (ts, count) for ts, count in self.requests[ip] if ts > window
        ]
        
        # Count total requests in window
        total = sum(count for _, count in self.requests[ip])
        
        if total >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return True
        
        # Add current request
        self.requests[ip].append((now, 1))
        return False


class SecurityHeaders:
    """Security headers middleware"""
    
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }


def add_security_headers(response):
    """Add security headers to response"""
    for key, value in SecurityHeaders.HEADERS.items():
        response.headers[key] = value
    return response


class RequestSanitizer:
    """Sanitizes user input"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
        
        Returns:
            Sanitized string
        
        Raises:
            HTTPException: If input is invalid
        """
        if not isinstance(value, str):
            return value
        
        # Check length
        if len(value) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input exceeds maximum length of {max_length}"
            )
        
        # Strip whitespace
        value = value.strip()
        
        # Validate for injection
        SecurityValidator.validate_input(value)
        
        return value
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Validate and sanitize email"""
        email = email.strip().lower()
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        return email
    
    @staticmethod
    def sanitize_number(value: Any, min_val: float = None, max_val: float = None) -> float:
        """Validate and sanitize numeric input"""
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid numeric value"
            )
        
        if min_val is not None and num < min_val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Value must be >= {min_val}"
            )
        
        if max_val is not None and num > max_val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Value must be <= {max_val}"
            )
        
        return num


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=100)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        if rate_limiter.is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "Rate limit exceeded"}
            )
        
        return await call_next(request)




