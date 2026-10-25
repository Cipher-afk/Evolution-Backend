from fastapi import FastAPI
from db_config import init_db
from routers.auth.routes import router as auth_router
from routers.goals.router import router as goal_router
from routers.tasks.routes import router as task_router
from routers.user.routes import router as user_router


async def lifespan(app: FastAPI):
    print("Server Starting....")
    await init_db()
    yield
    print("Server Ending")


app = FastAPI(title="Evolution", lifespan=lifespan)

app.include_router(router=auth_router, prefix="/auth", tags=["Auth"])
app.include_router(router=user_router,prefix='/user',tags=['User'])
app.include_router(router=goal_router, prefix="/goal", tags=["Goal"])
app.include_router(router=task_router, prefix="/task", tags=["Task"])
