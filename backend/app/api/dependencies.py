from fastapi import Request

from app.composition import Container


def get_container(request: Request) -> Container:
    """The only reader of app.state: routes receive the container through Depends."""
    container: Container = request.app.state.container
    return container
