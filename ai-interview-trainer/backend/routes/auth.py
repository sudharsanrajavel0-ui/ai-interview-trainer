from fastapi import APIRouter, Depends, HTTPException, Request, status
import re
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, LoginEvent
from backend.schemas import UserCreate, UserLogin, UserResponse, Token
from backend.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# CHANGED: Email domain validation — only @gmail.com addresses are allowed
EMAIL_DOMAIN_ERROR = "Only @gmail.com email addresses are allowed."
_EMAIL_RE = re.compile(r"^[^@\s]+@gmail\.com$", re.IGNORECASE)


# CHANGED: Email domain validation
def _has_valid_email_domain(email: str) -> bool:
    if not email:
        return False
    # CHANGED: reject leading/trailing whitespace and any non-gmail.com domain
    return bool(_EMAIL_RE.match(email.strip()))


# CHANGED: Password policy — preserve existing minimum length and add strict rules.
# Allowed special characters are only ! and @; passwords must also contain at
# least one uppercase letter, one lowercase letter and one number.
_PASSWORD_MIN_LENGTH = 6
_PASSWORD_UPPER_RE = re.compile(r"[A-Z]")
_PASSWORD_LOWER_RE = re.compile(r"[a-z]")
_PASSWORD_DIGIT_RE = re.compile(r"[0-9]")
# Allowed special characters: ! and @ only
_PASSWORD_DISALLOWED_SPECIAL_RE = re.compile(r"[^A-Za-z0-9!@]")


def _validate_password_policy(password: str) -> str | None:
    if len(password) < _PASSWORD_MIN_LENGTH:
        return "Password must be at least 6 characters long."
    if not _PASSWORD_UPPER_RE.search(password):
        return "Password must contain at least one uppercase letter."
    if not _PASSWORD_LOWER_RE.search(password):
        return "Password must contain at least one lowercase letter."
    if not _PASSWORD_DIGIT_RE.search(password):
        return "Password must contain at least one number."
    if _PASSWORD_DISALLOWED_SPECIAL_RE.search(password):
        return "Password may contain only ! and @ as special characters."
    return None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # CHANGED: normalize surrounding whitespace before validation
    email = user.email.strip()

    # CHANGED: Email domain validation before account creation
    if not _has_valid_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_DOMAIN_ERROR,
        )

    # CHANGED: Password policy validation before account creation
    password_error = _validate_password_policy(user.password)
    if password_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=password_error,
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        full_name=user.full_name,
        email=email,
        hashed_password=hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(user: UserLogin, request: Request, db: Session = Depends(get_db)):
    # CHANGED: normalize surrounding whitespace before validation
    email = user.email.strip()

    # CHANGED: Email domain validation before authentication
    if not _has_valid_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=EMAIL_DOMAIN_ERROR,
        )

    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        # Record failed login attempt if we have the email
        try:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            login_event = LoginEvent(
                user_id=None,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=0,
            )
            db.add(login_event)
            db.commit()
        except Exception:
            pass  # Do not interfere with login flow
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    # CHANGED: Password notification — distinct message for an incorrect password
    if not verify_password(user.password, db_user.hashed_password):
        try:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            login_event = LoginEvent(
                user_id=db_user.id,
                email=db_user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=0,
            )
            db.add(login_event)
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again.",
        )

    # Record successful login
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        login_event = LoginEvent(
            user_id=db_user.id,
            email=db_user.email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=1,
        )
        db.add(login_event)
        db.commit()
    except Exception:
        pass  # Do not prevent login on logging failure

    access_token = create_access_token(data={"sub": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
