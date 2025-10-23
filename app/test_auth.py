"""Unit tests for authentication functionality."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from auth import authenticate_user, create_access_token, verify_token
from settings import settings


class TestAuthentication:
    """Test cases for authentication functionality."""
    
    def test_authenticate_user_valid(self):
        """Test valid user authentication."""
        assert authenticate_user(settings.admin_user, settings.admin_pass) == True
    
    def test_authenticate_user_invalid_username(self):
        """Test invalid username authentication."""
        assert authenticate_user("wrong_user", settings.admin_pass) == False
    
    def test_authenticate_user_invalid_password(self):
        """Test invalid password authentication."""
        assert authenticate_user(settings.admin_user, "wrong_pass") == False
    
    def test_authenticate_user_both_invalid(self):
        """Test both username and password invalid."""
        assert authenticate_user("wrong_user", "wrong_pass") == False
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_valid(self):
        """Test valid token verification."""
        data = {"sub": "test_user"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
    
    def test_verify_token_invalid(self):
        """Test invalid token verification."""
        invalid_token = "invalid.jwt.token"
        
        payload = verify_token(invalid_token)
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test expired token verification."""
        data = {"sub": "test_user"}
        # Create token with very short expiry
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)
        
        payload = verify_token(token)
        assert payload is None



