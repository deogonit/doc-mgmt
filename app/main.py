from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi import utils as openapi_utils
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# logger config
from app import log_config  # noqa: F401


def init_routers(application):
    from app.api.base.api import api_base_router
    from app.api.v1.api import api_v1_router

    application.include_router(api_base_router)
    application.include_router(api_v1_router)


def create_app() -> FastAPI:
    from app.base.schema import ValidationError
    from app.container import Container

    container = Container()
    application = FastAPI(
        title="DocManagement",
        description="API Document Management Service",
        version="1.0",
        debug=False,
    )

    # events
    @application.on_event("startup")
    async def startup():
        await container.init_resources()  # type: ignore

    @application.on_event("shutdown")
    async def shutdown():
        await container.shutdown_resources()  # type: ignore

    # middlewares
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            loc = error.get("loc")
            msg = error.get("msg")
            msg_type = error.get("type")

            if not (loc and msg and msg_type):
                continue

            match len(loc):
                case length if length == 1:
                    field = loc[0]
                case length if length == 2:
                    field = loc[1]
                case _:
                    field = ".".join([str(field) for field in loc[1:]])

            errors.append(ValidationError(field=field, message=msg, type=msg_type))

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": [err.dict() for err in errors]},
        )

    # ValidationError is hardcoded in FastApi and this is only one possible way
    # to redefine ValidationError model in OpenAPI (Swagger)
    openapi_utils.validation_error_definition = {
        "title": "ValidationError",
        "type": "object",
        "properties": {
            "message": {
                "title": "Message",
                "type": "string"
            },
            "field": {
                "title": "Field",
                "type": "string"
            },
            "type": {
                "title": "Error Type",
                "type": "string"
            },
        },
        "required": ["location", "message", "type"],
    }

    # routers
    init_routers(application)

    application.container = container  # type: ignore

    return application


app = create_app()
