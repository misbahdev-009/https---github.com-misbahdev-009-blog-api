from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from ..database import users
from ..schemas import UserCreate, UserOut, Token
from ..security import verify_password, create_access_token, get_current_user
from ..services import create_user
from ..utils import serialize

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate):
    """Create a new account. The very first account is made an admin."""
    user = await create_user(payload.name, payload.email, payload.password)
    return serialize(user)


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Log in with your email (as `username`) and password to get a JWT token."""
    user = await users.find_one({"email": form.username.lower().strip()})
    if not user or not verify_password(form.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(str(user["_id"])), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return serialize(user)
