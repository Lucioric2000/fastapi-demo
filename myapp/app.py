# main/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models
from . import schemas
from . dependencies.auth import get_db, TokenData, authenticate_user, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
from cachetools import TTLCache

app = FastAPI()

# Initialize cache with 5 minutes TTL
cache = TTLCache(maxsize=100, ttl=300)

@app.post("/signup", response_model=schemas.Token)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(email=user.email, hashed_password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/addpost", response_model=schemas.Post)
def add_post(post: schemas.PostCreate, token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")), db: Session = Depends(get_db)):
    if len(post.text.encode('utf-8')) > 1e6:  # Check if payload size exceeds 1 MB
        raise HTTPException(status_code=413, detail="Payload too large")
    current_user = get_current_user(token, db)
    db_post = models.Post(text=post.text, owner_id=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

@app.get("/getposts", response_model=List[schemas.Post])
def get_posts(token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")), db: Session = Depends(get_db)):
    current_user = get_current_user(token, db)
    if current_user.id in cache:
        return cache[current_user.id]
    posts = db.query(models.Post).filter(models.Post.owner_id == current_user.id).all()
    cache[current_user.id] = posts
    return posts

@app.delete("/deletepost/{post_id}")
def delete_post(post_id: int, token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")), db: Session = Depends(get_db)):
    current_user = get_current_user(token, db)
    db_post = db.query(models.Post).filter(models.Post.id == post_id, models.Post.owner_id == current_user.id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}