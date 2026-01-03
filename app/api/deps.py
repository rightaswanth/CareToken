from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import PyJWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models import User
from app.db.session import get_session
from sqlmodel import select

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (PyJWTError, ValidationError):
        raise credentials_exception
    
    # Verify with Redis
    from app.core.redis import redis_client
    import json
    
    token_data_json = await redis_client.get_token(token)
    if not token_data_json:
        raise credentials_exception
        
    token_data = json.loads(token_data_json)
    if token_data.get("type") != "admin":
        raise credentials_exception

    user = await session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user

from app.db.models import AppUser

async def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> AppUser:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (PyJWTError, ValidationError):
        raise credentials_exception
    
    # Verify with Redis
    from app.core.redis import redis_client
    import json
    
    token_data_json = await redis_client.get_token(token)
    if not token_data_json:
        raise credentials_exception
        
    token_data = json.loads(token_data_json)
    if token_data.get("type") != "patient":
        raise credentials_exception

    user = await session.get(AppUser, user_id)
    if user is None:
        raise credentials_exception
    return user

from typing import Union, Optional

async def get_current_user_or_patient(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Union[User, AppUser]:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (PyJWTError, ValidationError):
        raise credentials_exception
    
    # Verify with Redis
    from app.core.redis import redis_client
    import json
    
    token_data_json = await redis_client.get_token(token)
    if not token_data_json:
        raise credentials_exception
        
    token_data = json.loads(token_data_json)
    user_type = token_data.get("type")
    
    if user_type == "admin":
        user = await session.get(User, user_id)
    elif user_type == "patient":
        user = await session.get(AppUser, user_id)
    else:
        raise credentials_exception

    if user is None:
        raise credentials_exception
    return user

security_optional = HTTPBearer(auto_error=False)

async def get_current_user_or_patient_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    session: AsyncSession = Depends(get_session)
) -> Union[User, AppUser, None]:
    if not credentials:
        return None
        
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except (PyJWTError, ValidationError):
        return None
    
    # Verify with Redis
    from app.core.redis import redis_client
    import json
    
    token_data_json = await redis_client.get_token(token)
    if not token_data_json:
        return None
        
    token_data = json.loads(token_data_json)
    user_type = token_data.get("type")
    
    if user_type == "admin":
        user = await session.get(User, user_id)
    elif user_type == "patient":
        user = await session.get(AppUser, user_id)
    else:
        return None

    return user
