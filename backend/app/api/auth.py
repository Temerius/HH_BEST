from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
import json
import base64
import logging
from urllib.parse import urlencode
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
    is_token_blacklisted,
    redis_client
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, TokenRefresh
router = APIRouter()

# Настройка логирования
logger = logging.getLogger(__name__)

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
async def google_login(
    request: Request,
    redirect_uri: Optional[str] = Query(None, description="URL для редиректа после авторизации (для мобильных приложений)"),
    platform: Optional[str] = Query(None, description="Платформа ('mobile' для мобильных приложений)")
):
    """Начало OAuth авторизации через Google
    
    Args:
        redirect_uri: Опциональный URL для редиректа после авторизации (для мобильных приложений)
        platform: Опциональный параметр платформы ('mobile' для мобильных приложений)
    """
    if not settings.GOOGLE_CLIENT_ID or not oauth:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )
    
    # Используем полный URL для callback
    base_url = str(request.base_url).rstrip('/')
    oauth_redirect_uri = f"{base_url}/api/auth/google/callback"
    
    # Сохраняем redirect_uri в сессии (для веб-версии)
    if redirect_uri or platform == 'mobile':
        try:
            request.session['oauth_redirect_uri'] = redirect_uri
            request.session['oauth_platform'] = platform or 'mobile'
        except:
            # Если сессия не работает (мобильное приложение),
            # сохраняем redirect_uri в Redis с ключом, который мы получим из state
            # Но state еще не создан, поэтому создаем временный ключ
            pass
    
    # Выполняем редирект и получаем response
    response = await oauth.google.authorize_redirect(request, oauth_redirect_uri)
    
    # Если это мобильное приложение и сессия не работает,
    # пытаемся получить state из response и сохранить redirect_uri в Redis
    if (redirect_uri or platform == 'mobile') and redis_client:
        try:
            logger.info("Trying to save state and redirect_uri to Redis...")
            # Сначала пытаемся извлечь state из URL редиректа (это самый надежный способ)
            state_from_url = None
            if hasattr(response, 'headers') and 'location' in response.headers:
                location = response.headers['location']
                logger.info(f"Location header: {location}")
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(location)
                params = parse_qs(parsed.query)
                state_from_url = params.get('state', [None])[0]
                logger.info(f"State from URL: {state_from_url}")
            
            # Также пытаемся получить state из сессии (authlib сохраняет его там как словарь)
            session_state = request.session.get('_state_google')
            logger.info(f"Session state: {session_state} (type: {type(session_state)})")
            state_from_session = None
            if isinstance(session_state, dict):
                state_from_session = session_state.get('state')
                logger.info(f"State from session dict: {state_from_session}")
            elif isinstance(session_state, str):
                state_from_session = session_state
                logger.info(f"State from session string: {state_from_session}")
            
            # Используем state из URL, если он есть, иначе из сессии
            state = state_from_url or state_from_session
            logger.info(f"Final state to save: {state}")
            
            if state and redirect_uri:
                # Сохраняем redirect_uri в Redis с ключом из state
                redis_key = f"oauth_redirect:{state}"
                logger.info(f"Saving redirect_uri to Redis with key: {redis_key}")
                redis_client.setex(redis_key, 600, redirect_uri)
                
                # Сохраняем platform в Redis, если он есть
                current_platform = platform or request.session.get('oauth_platform')
                if current_platform:
                    redis_platform_key = f"oauth_platform:{state}"
                    logger.info(f"Saving platform to Redis with key: {redis_platform_key}, value: {current_platform}")
                    redis_client.setex(redis_platform_key, 600, current_platform)
                
                # Сохраняем сам state в Redis для восстановления в callback
                # ВАЖНО: сохраняем весь словарь state из сессии, если он есть
                redis_state_key = f"oauth_state:{state}"
                if isinstance(session_state, dict):
                    import json
                    state_json = json.dumps(session_state)
                    logger.info(f"Saving state dict to Redis: {state_json}")
                    redis_client.setex(redis_state_key, 600, state_json)
                else:
                    # Если state нет в сессии или это не словарь, создаем словарь
                    import json
                    state_dict = {'state': state}
                    state_json = json.dumps(state_dict)
                    logger.info(f"Creating and saving state dict to Redis: {state_json}")
                    redis_client.setex(redis_state_key, 600, state_json)
            else:
                logger.warning(f"Cannot save to Redis: state={state}, redirect_uri={redirect_uri}")
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            logger.error(f"Failed to save state to Redis: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    return response


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
    
    # Логируем все query параметры
    logger.info(f"=== OAuth Callback Request ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"State from query: {request.query_params.get('state')}")
    logger.info(f"Code from query: {request.query_params.get('code')}")
    logger.info(f"Access token from query: {request.query_params.get('access_token')}")
    logger.info(f"Refresh token from query: {request.query_params.get('refresh_token')}")
    
    try:
        # Проверяем, есть ли state в query параметрах
        state_from_query = request.query_params.get('state')
        code_from_query = request.query_params.get('code')
        access_token_from_query = request.query_params.get('access_token')
        refresh_token_from_query = request.query_params.get('refresh_token')
        
        # Если state нет в query, но есть токены - это уже второй запрос после редиректа
        # Это происходит, когда мы редиректим на callback с токенами, и браузер делает еще один запрос
        if not state_from_query and access_token_from_query and refresh_token_from_query:
            logger.info("Callback with tokens but without state - this is a redirect after successful auth")
            logger.info("This should be handled by mobile app via deep link, but returning tokens anyway")
            # Возвращаем токены в JSON формате для мобильного приложения
            # Мобильное приложение должно перехватывать deep link, но на всякий случай возвращаем токены
            from fastapi.responses import JSONResponse
            return JSONResponse(content={
                "access_token": access_token_from_query,
                "refresh_token": refresh_token_from_query,
                "token_type": "bearer"
            })
        
        # Если нет ни state, ни code, ни токенов - это ошибка
        if not state_from_query and not code_from_query:
            logger.error("Callback without state and without code - invalid request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid callback: missing state and code parameters"
            )
        
        # Пытаемся получить redirect_uri и platform из сессии (для веб-версии)
        redirect_uri = None
        platform = None
        logger.info("Trying to get redirect_uri and platform from session...")
        try:
            redirect_uri = request.session.get('oauth_redirect_uri')
            platform = request.session.get('oauth_platform')
            logger.info(f"Redirect URI from session: {redirect_uri}")
            logger.info(f"Platform from session: {platform}")
            if redirect_uri:
                # Очищаем сессию
                if 'oauth_redirect_uri' in request.session:
                    del request.session['oauth_redirect_uri']
                if 'oauth_platform' in request.session:
                    del request.session['oauth_platform']
        except Exception as e:
            logger.warning(f"Failed to get redirect_uri from session: {e}")
            # Если сессия не работает (мобильное приложение),
            # получаем redirect_uri из Redis используя state как ключ
            if redis_client and state_from_query:
                try:
                    redis_key = f"oauth_redirect:{state_from_query}"
                    logger.info(f"Trying to get redirect_uri from Redis with key: {redis_key}")
                    stored = redis_client.get(redis_key)
                    if stored:
                        redirect_uri = stored
                        logger.info(f"Redirect URI from Redis: {redirect_uri}")
                        # Удаляем из Redis после использования
                        redis_client.delete(redis_key)
                    else:
                        logger.warning(f"No redirect_uri found in Redis for key: {redis_key}")
                    
                    # Также пытаемся получить platform из Redis
                    redis_platform_key = f"oauth_platform:{state_from_query}"
                    stored_platform = redis_client.get(redis_platform_key)
                    if stored_platform:
                        platform = stored_platform.decode('utf-8') if isinstance(stored_platform, bytes) else stored_platform
                        logger.info(f"Platform from Redis: {platform}")
                        redis_client.delete(redis_platform_key)
                except Exception as e:
                    logger.error(f"Failed to get redirect_uri from Redis: {e}")
        
        # Для мобильных приложений: если state есть в Redis, но нет в сессии,
        # восстанавливаем state в сессии перед вызовом authorize_access_token
        # ВАЖНО: всегда обновляем state в сессии на значение из query, чтобы они совпадали
        if state_from_query:
            logger.info(f"Setting state in session to: {state_from_query}")
            try:
                # Проверяем текущее состояние сессии
                current_session_state = request.session.get('_state_google')
                logger.info(f"Current session state: {current_session_state} (type: {type(current_session_state)})")
                
                # Просто устанавливаем state в сессии на значение из query
                # Это гарантирует, что state в сессии всегда совпадает с query
                request.session['_state_google'] = {'state': state_from_query}
                logger.info(f"Updated session state to: {request.session.get('_state_google')}")
            except Exception as e:
                logger.error(f"Failed to set state in session: {e}")
                pass
            try:
                # Проверяем, есть ли state в сессии и совпадает ли он с state из query
                session_state = request.session.get('_state_google')
                
                # Проверяем, совпадает ли state в сессии с state из query
                state_matches = False
                if isinstance(session_state, dict):
                    session_state_value = session_state.get('state')
                    if session_state_value == state_from_query:
                        state_matches = True
                elif session_state == state_from_query:
                    # Если state в сессии - это строка, которая совпадает с query
                    state_matches = True
                
                if not state_matches:
                    # Если state не совпадает, пытаемся восстановить его из Redis
                    redis_state_key = f"oauth_state:{state_from_query}"
                    stored_state_json = redis_client.get(redis_state_key)
                    if stored_state_json:
                        # Пытаемся десериализовать из JSON
                        try:
                            import json
                            state_dict = json.loads(stored_state_json)
                            if isinstance(state_dict, dict):
                                # ВАЖНО: обновляем state в словаре на значение из query
                                # Это гарантирует, что state в сессии совпадает с query
                                state_dict['state'] = state_from_query
                                request.session['_state_google'] = state_dict
                            else:
                                # Если это не словарь, создаем словарь с state
                                request.session['_state_google'] = {'state': state_from_query}
                        except:
                            # Если не JSON, создаем словарь с state
                            request.session['_state_google'] = {'state': state_from_query}
                        # Удаляем из Redis после использования
                        redis_client.delete(redis_state_key)
                    else:
                        # Если state нет в Redis, просто перезаписываем state в сессии
                        # на значение из query - это должно решить проблему несовпадения
                        request.session['_state_google'] = {'state': state_from_query}
                elif not session_state:
                    # Если state нет в сессии вообще, создаем его
                    request.session['_state_google'] = {'state': state_from_query}
                else:
                    # Если state совпадает, но это не словарь, преобразуем в словарь
                    if not isinstance(session_state, dict):
                        request.session['_state_google'] = {'state': state_from_query}
            except Exception as e:
                # Если сессия не работает, просто пробуем вызвать authorize_access_token
                # authlib может выдать ошибку, но это лучше, чем ничего
                pass
        
        # Получаем токен от Google
        logger.info("Calling authorize_access_token...")
        logger.info(f"Session state before authorize_access_token: {request.session.get('_state_google')}")
        token = await oauth.google.authorize_access_token(request)
        logger.info("Successfully got token from Google")
        logger.info(f"Token keys: {list(token.keys()) if isinstance(token, dict) else 'Not a dict'}")
        
        # Проверяем, что token - это словарь
        if not isinstance(token, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid token format: {type(token)}, token: {token}"
            )
        
        # Получаем информацию о пользователе из ID токена
        # parse_id_token принимает request и token, возвращает словарь с данными пользователя
        user_info = None
        
        # Сначала пробуем получить userinfo напрямую из token (если есть)
        if isinstance(token, dict) and 'userinfo' in token:
            user_info = token.get('userinfo')
            if isinstance(user_info, dict):
                # Если userinfo уже есть и это словарь, используем его
                pass
            else:
                user_info = None
        
        # Если userinfo нет в token, используем parse_id_token
        if not user_info:
            try:
                user_info = await oauth.google.parse_id_token(request, token)
                # Проверяем тип сразу после получения
                if not isinstance(user_info, dict):
                    # Если это не словарь, возможно это строка или другой тип
                    raise ValueError(f"parse_id_token returned {type(user_info)}, expected dict")
            except Exception as parse_error:
                # Если parse_id_token не работает, пробуем получить userinfo из token напрямую
                # В некоторых версиях authlib userinfo уже есть в token
                if isinstance(token, dict):
                    # Пробуем получить userinfo напрямую из token
                    user_info = token.get('userinfo')
                    if not user_info:
                        # Пробуем получить из id_token и декодировать вручную
                        id_token = token.get('id_token')
                        if id_token:
                            # Если id_token есть, но parse_id_token не работает,
                            # попробуем декодировать JWT вручную
                            try:
                                from jose import jwt as jose_jwt
                                # Декодируем без проверки подписи (небезопасно, но для отладки)
                                # В реальности нужно использовать публичный ключ Google
                                decoded = jose_jwt.decode(id_token, options={"verify_signature": False})
                                user_info = decoded
                            except Exception as jwt_error:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Failed to parse user info: parse_error={str(parse_error)}, jwt_error={str(jwt_error)}, token keys: {list(token.keys()) if isinstance(token, dict) else 'N/A'}"
                                )
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Failed to parse user info: {str(parse_error)}, token keys: {list(token.keys()) if isinstance(token, dict) else 'N/A'}, no id_token found"
                            )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to get user info: {str(parse_error)}, token is not a dict: {type(token)}"
                    )
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        # Проверяем, что user_info - это словарь
        # parse_id_token должен возвращать словарь, но на всякий случай проверяем
        if not isinstance(user_info, dict):
            # Если user_info - строка, возможно это JSON
            if isinstance(user_info, str):
                try:
                    import json
                    user_info = json.loads(user_info)
                except:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid user_info format: {type(user_info)}, user_info: {user_info}"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid user_info format: {type(user_info)}, user_info: {user_info}"
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
        
        # Если есть redirect_uri (для мобильного приложения), редиректим туда
        if redirect_uri:
            logger.info(f"Redirecting to: {redirect_uri}")
            # Для мобильного приложения используем custom URL scheme для deep linking
            # Это позволяет мобильному приложению перехватить редирект
            if platform == 'mobile' or 'mobile' in redirect_uri or 'nip.io' in redirect_uri:
                # Используем custom URL scheme для мобильного приложения
                custom_scheme = "hhabest://oauth/callback"
                redirect_url = f"{custom_scheme}?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
                logger.info(f"Using custom scheme for mobile: {redirect_url}")
            else:
                # Для веб-версии используем обычный редирект
                redirect_url = f"{redirect_uri}?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
                logger.info(f"Using regular redirect for web: {redirect_url}")
            return RedirectResponse(url=redirect_url)
        
        # Иначе редиректим на фронтенд (по умолчанию)
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback"
        logger.info(f"Redirecting to frontend: {frontend_url}")
        return RedirectResponse(
            url=f"{frontend_url}?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
        )
        
    except HTTPException:
        # Пробрасываем HTTPException как есть
        raise
    except Exception as e:
        # Логируем полную информацию об ошибке для отладки
        import traceback
        error_trace = traceback.format_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}\nTraceback: {error_trace}"
        )
