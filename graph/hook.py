import inspect
from typing import Callable, Union


class hookable:
    def __init__(self, dont_hook=None):
        self.dont_hook = dont_hook or set()
        self.dont_hook.add('regsiter_callback')

    def __call__(self, cls):
        setattr(cls, "__originals", {})
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for attr, value in methods:
            if attr == "__init__":
                # print("making init hookable")
                setattr(cls, attr, wrap_init(value))
                continue
            if attr in self.dont_hook:
                continue
            # print("making", attr, "hookable")
            getattr(cls, '__originals')[attr] = value
            setattr(cls, attr, wrap_hookable(attr, value))
        if '__init__' not in cls.__dict__:
            # print("making init hookable")
            setattr(cls, '__init__', wrap_init(lambda self: self))
        if not hasattr(cls, 'regsiter_callback'):
            setattr(cls, 'register_callback', Hookable.register_callback)
        return cls


def wrap_init(init_func):
    def init(self, *args, **kwargs):
        init_func(self, *args, **kwargs)
        setattr(self, '__hooks', {})
    
    return init


def wrap_hookable(func_name, func):
    def hookable_func(self, *args, **kwargs):
        for hook in self.__hooks.get(func_name, []):
            hook(*args, **kwargs)
        return func(self, *args, **kwargs)
    hookable_func.__name__ = func_name
    return hookable_func


class Hookable:
    def register_callback(self, func_name: Union[Callable, str], hook: Callable):
        if not isinstance(func_name, str):
            func_name = func_name.__name__
        hooks = getattr(self, '__hooks')
        if func_name not in hooks:
            hooks[func_name] = list()
        hooks[func_name].append(hook)


@hookable()
class A(Hookable):
    def get1(self):
        return 1
    
    def get2(self):
        return 2


def main():
    a: A = A()
    a.register_callback(a.get1, lambda self: print("calling get 1"))
    a.register_callback(a.get2, lambda self: print("calling get 2"))
    a.get1()
    a.get2()


if __name__ == "__main__":
    main()