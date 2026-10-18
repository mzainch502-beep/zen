"""Adapt synchronous FastAPI handlers to Workers' single-thread Python runtime."""
import inspect
from functools import wraps
from fastapi.routing import APIRoute
from starlette.routing import request_response

def asynchronous(function):
    if inspect.iscoroutinefunction(function) or inspect.isasyncgenfunction(function):
        return function
    if inspect.isgeneratorfunction(function):
        async def generator(*args, **kwargs):
            with __import__('contextlib').contextmanager(function)(*args, **kwargs) as value:
                yield value
        generator.__signature__ = inspect.signature(function)
        generator.__name__ = function.__name__
        return generator
    async def call(*args, **kwargs):
        return function(*args, **kwargs)
    call.__signature__ = inspect.signature(function)
    call.__name__ = function.__name__
    return call

def adapt(app):
    def walk(dependant):
        dependant.call = asynchronous(dependant.call)
        # FastAPI computes these properties from the dependency callable.
        if hasattr(dependant, '__dict__'):
            for key in ('is_coroutine_callable', 'is_gen_callable', 'is_async_gen_callable'):
                dependant.__dict__.pop(key, None)
        for child in dependant.dependencies: walk(child)
    for route in app.routes:
        if isinstance(route, APIRoute):
            walk(route.dependant)
            route.endpoint = route.dependant.call
            route.app = request_response(route.get_route_handler())
    return app
