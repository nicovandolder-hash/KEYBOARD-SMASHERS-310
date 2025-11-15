from fastapi import HTTPException, status, Cookie, Depends
from typing import Optional, Annotated
import secrets
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

sessions = {}

SESSION_TIMEOUT = timedelta(hours=2)

class SessionManager:
    
    @staticmethod
    def create_session(user_id: str) -> str:
        session_token = secrets.token_urlsafe(32)
        sessions[session_token] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + SESSION_TIMEOUT
        }
        logger.info(f"Session created for user: {user_id}")
        return session_token
    
    @staticmethod
    def validate_session(session_token: str) -> Optional[str]:
        if not session_token or session_token not in sessions:
            return None
        
        session = sessions[session_token]

        if datetime.now() > session['expires_at']:
            logger.warning(f"Expired session attempt: {session_token[:8]}...")
            del sessions[session_token]
            return None
        
        return session['user_id']
    
    @staticmethod
    def delete_session(session_token: str):
        if session_token in sessions:
            user_id = sessions[session_token]['user_id']
            del sessions[session_token]
            logger.info(f"Session deleted for user: {user_id}")
            return True
        return False
    
    @staticmethod
    def cleanup_expired_sessions():
        now = datetime.now()
        expired = [token for token, data in sessions.items() 
                   if now > data['expires_at']]
        for token in expired:
            del sessions[token]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

async def get_current_user(
    session_token: Annotated[Optional[str], Cookie(alias="session_token")] = None
) -> str:
    if not session_token:
        logger.warning("No session token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login."
        )
    
    user_id = SessionManager.validate_session(session_token)
    if not user_id:
        logger.warning(f"Invalid session token: {session_token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please login again."
        )
    
    return user_id

async def get_current_user_optional(
    session_token: Annotated[Optional[str], Cookie(alias="session_token")] = None
) -> Optional[str]:
    if not session_token:
        return None
    
    return SessionManager.validate_session(session_token)

async def get_current_admin_user(
    current_user_id: Annotated[str, Depends(get_current_user)]
) -> str:
    from keyboard_smashers.controllers.user_controller import user_controller_instance
    
    user = user_controller_instance.get_user_by_id(current_user_id)
    if not user or not user.is_admin:
        logger.warning(f"Non-admin user attempted admin action: {current_user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user_id