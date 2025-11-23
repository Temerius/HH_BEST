from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_access_token
)
from app.core.config import settings
from app.core.redis_client import (
    store_refresh_token,
    get_refresh_token,
    delete_refresh_token,
    add_to_blacklist,
    is_token_blacklisted
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, TokenRefresh
router = APIRouter()

# OAuth конфигурация (будет инициализирована при наличии credentials)
oauth = None

def init_oauth():
    """Инициализация OAuth"""
    global oauth
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        try:
            from authlib.integrations.starlette_client import OAuth
            from starlette.config import Config
            config = Config()
            oauth = OAuth(config)
            oauth.register(
                name='google',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
        except ImportError:
            pass

# Инициализируем при импорте модуля
init_oauth()


def _create_tokens(user: User) -> dict:
    """Создание access и refresh токенов"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    # Сохраняем refresh токен в Redis
    refresh_expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    store_refresh_token(str(user.id), refresh_token, refresh_expire_seconds)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        # Если пользователь существует и у него есть пароль - email занят
        if existing_user.password_hash and existing_user.password_hash.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please use login instead."
            )
        # Если пользователь существует, но без пароля (OAuth) - устанавливаем пароль
        else:
            # Обновляем существующего OAuth пользователя, добавляя пароль
            hashed_password = get_password_hash(user_data.password)
            existing_user.password_hash = hashed_password
            if user_data.first_name:
                existing_user.first_name = user_data.first_name
            if user_data.last_name:
                existing_user.last_name = user_data.last_name
            if user_data.phone:
                existing_user.phone = user_data.phone
            if user_data.birth_date:
                existing_user.birth_date = user_data.birth_date
            
            db.commit()
            db.refresh(existing_user)
            return existing_user
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        birth_date=user_data.birth_date
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Вход пользователя и получение JWT токенов"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем, есть ли пароль у пользователя (OAuth пользователи не имеют пароля)
    if not user.password_hash or user.password_hash.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account was created via OAuth. Please use Google login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return _create_tokens(user)


@router.post("/login-json", response_model=Token)
async def login_json(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """Вход пользователя через JSON (альтернативный endpoint)"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем, есть ли пароль у пользователя
    if not user.password_hash or user.password_hash.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account was created via OAuth. Please use Google login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    return _create_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Обновление access токена с помощью refresh токена"""
    payload = decode_refresh_token(token_data.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("user_id")
    email = payload.get("sub")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Проверяем, что refresh токен сохранен в Redis
    stored_token = get_refresh_token(user_id)
    if stored_token != token_data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or expired"
        )
    
    # Получаем пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Создаем новые токены
    return _create_tokens(user)


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Выход пользователя (добавление токена в блэклист)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Декодируем токен для получения времени истечения
    payload = decode_access_token(token)
    if payload:
        exp = payload.get("exp")
        if exp:
            # Вычисляем время до истечения токена
            from datetime import datetime
            expire_time = datetime.fromtimestamp(exp)
            now = datetime.utcnow()
            expire_seconds = int((expire_time - now).total_seconds())
            
            if expire_seconds > 0:
                # Добавляем токен в блэклист
                add_to_blacklist(token, expire_seconds)
    
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(
    refresh_token: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Выход из всех устройств (удаление всех refresh токенов)"""
    payload = decode_refresh_token(refresh_token.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("user_id")
    if user_id:
        delete_refresh_token(user_id)
    
    return {"message": "Logged out from all devices"}


# OAuth Google endpoints
@router.get("/google/login")
async def google_login(request: Request):
    """Начало OAuth авторизации через Google"""
    if not settings.GOOGLE_CLIENT_ID or not oauth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )
    
    # Используем полный URL для callback
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Callback для OAuth авторизации через Google"""
    if not settings.GOOGLE_CLIENT_ID or not oauth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )
    
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        email = user_info.get('email')
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        # Ищем или создаем пользователя
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Создаем нового пользователя
            # Получаем аватарку из Google (если есть)
            picture = user_info.get('picture')
            user = User(
                email=email,
                password_hash="",  # OAuth пользователи не имеют пароля
                first_name=user_info.get('given_name'),
                last_name=user_info.get('family_name'),
                avatar_url=picture if picture else None,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Обновляем аватарку, если её нет, но есть в Google
            if not user.avatar_url and user_info.get('picture'):
                user.avatar_url = user_info.get('picture')
                db.commit()
                db.refresh(user)
        
        # Создаем токены
        tokens = _create_tokens(user)
        
        # Перенаправляем на фронтенд с токенами
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback"
        return RedirectResponse(
            url=f"{frontend_url}?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}"
        )
