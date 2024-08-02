from fastapi import FastAPI, Request, status
from routes.routes import router as api_router
from config.db import connect_mongodb
import uvicorn
from dotenv import dotenv_values
from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import session
from fastapi.responses import JSONResponse
from supertokens_python.recipe.session.exceptions import UnauthorisedError, TryRefreshTokenError
from fastapi.responses import JSONResponse
config = dotenv_values(".env")

init(
    app_info=InputAppInfo(
        app_name="authBackend",
        api_domain="http://localhost:8000",
        website_domain="http://localhost:3000",
        api_base_path="/auth",
        website_base_path="/auth"
    ),
    supertokens_config=SupertokensConfig(
        connection_uri="https://st-dev-fa72a220-3f68-11ef-bc8e-65def744e887.aws.supertokens.io",
        api_key="zYFhwyhtP2QbI=hHsknG7D-e3X",
    ),
    framework='fastapi',
    recipe_list=[
        session.init()
    ],
    mode='asgi'
)

app = FastAPI()

@app.on_event("startup")
def connect_db() :
    connection_mongo = connect_mongodb(app)
    print(connection_mongo)

@app.exception_handler(UnauthorisedError)
async def invalid_session_exception_handler(request: Request, exc: UnauthorisedError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": "Invalid or expired session. Please login again."}
    )

@app.exception_handler(TryRefreshTokenError)
async def invalid_session_exception_handler(request: Request, exc: TryRefreshTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": "Expired session. Use Refresh token"}
    )

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host='0.0.0.0', port=8000)