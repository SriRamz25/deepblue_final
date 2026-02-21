"""
Authentication Pydantic models for request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    """Request model for user signup."""
    
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=4, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    upi_id: str = Field(..., min_length=3, max_length=50, description="UPI ID must exist in transaction history (e.g. user1@upi)")
    
    @validator('password')
    def password_strength(cls, v):
        """Allow 4-digit numeric pins or standard passwords."""
        if v.isdigit() and len(v) >= 4:
            return v
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long or a numeric PIN')
        return v

    @validator('upi_id')
    def upi_id_format(cls, v):
        """Basic UPI ID format check."""
        v = v.strip().lower()
        if '@' not in v:
            raise ValueError('UPI ID must be in the format username@upi')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "gopal@gmail.com",
                "phone": "+919876543210",
                "password": "SecurePass123",
                "full_name": "Gopal Kumar",
                "upi_id": "user1@upi"
            }
        }


class LoginRequest(BaseModel):
    """Request model for user login."""
    
    phone: str
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "9876543210",
                "password": "SecurePass123"
            }
        }


class GoogleLoginRequest(BaseModel):
    """Request model for Google authentication."""
    id_token: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjRiZWU..."
            }
        }


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class UserResponse(BaseModel):
    """Response model for user data."""
    
    user_id: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    upi_id: Optional[str] = None
    trust_score: float
    risk_tier: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "USER-12345",
                "full_name": "Gopal Kumar",
                "phone": "9876543210",
                "email": "gopal@gmail.com",
                "upi_id": "gopal@okaxis",
                "trust_score": 0.0,
                "risk_tier": "BRONZE",
                "created_at": "2026-02-03T10:00:00Z"
            }
        }


class AuthResponse(BaseModel):
    """Complete authentication response with user data and token."""
    
    user_id: str
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    upi_id: Optional[str] = None
    trust_score: float
    risk_tier: str
    token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USER-12345",
                "full_name": "Gopal Kumar",
                "phone": "9876543210",
                "email": "gopal@gmail.com",
                "upi_id": "gopal@okaxis",
                "trust_score": 0.0,
                "risk_tier": "BRONZE",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
