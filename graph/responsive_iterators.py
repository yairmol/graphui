from typing import Callable, Generic, Iterable, Iterator, List, TypeVar, Optional

from graph.hook import Hookable

T = TypeVar('T')
NextCallback = Callable[[Optional[T], Optional[T]], None]


class ResponsiveIterable(Hookable):
    def __init__(self) -> None:
        self.next_cbs: List[NextCallback] = list()
    
    def register_on_next_callback(self, cb: NextCallback):
        self.next_cbs.append(cb)
        return len(self.next_cbs) - 1
    
    def clear_on_next_callbacks(self):
        self.next_cbs.clear()
    
    def remove_on_next_callback(self, cb_idx: int):
        if cb_idx >= len(self.next_cbs):
            raise IndexError(f"Out of range: {cb_idx} out of {len(self.next_cbs)}")
        return self.next_cbs.pop(cb_idx)


class ResponsiveIterator(Generic[T]):
    def __init__(self, iterator: Iterator[T], next_cbs=None) -> None:
        self.iterator = iterator
        self.next_callbacks: List[NextCallback] = next_cbs or []
    
    def __next__(self):
        item = next(self.iterator)
        for cb in self.next_callbacks:
            cb(item)
        return item

    def register_next_callback(self, cb: NextCallback):
        """
        register a callback and return its index in case of wanted removal
        """
        self.next_callbacks.append(cb)
        return len(self.next_callbacks) - 1
    
    def clear_callbacks(self):
        self.next_callbacks.clear()
    
    def remove_next_callback(self, idx: int):
        if idx >= len(self.next_callbacks):
            raise ValueError("Bad callback idx")
        self.next_callbacks.pop(idx)