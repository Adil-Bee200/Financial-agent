from fastapi import FastAPI
from app.routers import auth
from .routers import users, posts, votes
from . import models
from .database import engine
from fastapi.middleware.cors import CORSMiddleware