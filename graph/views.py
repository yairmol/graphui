from networkx.classes.coreviews import AtlasView, AdjacencyView
from networkx.classes.reportviews import NodeView, NodeDataView, EdgeView, EdgeDataView
from graph.hook import Hookable, hookable

from graph.responsive_iterators import ResponsiveIterable, ResponsiveIterator


class ResponsiveAtlasView(AtlasView, ResponsiveIterable):

    def __init__(self, d, cbs=None):
        AtlasView.__init__(self, d)
        ResponsiveIterable.__init__(self)
        self.cbs = cbs if cbs is not None else []
    
    def __iter__(self):
        return ResponsiveIterator(super().__iter__(), self.cbs)


@hookable()
class ResponsiveAdjacencyView(AdjacencyView, ResponsiveIterable):
    def __init__(self, d, cbs=None):
        AdjacencyView.__init__(self, d)
        ResponsiveIterable.__init__(self)
        self.cbs = cbs if cbs is not None else []
    
    def __iter__(self):
        return ResponsiveIterator(super().__iter__(), self.cbs)
    
    def __getitem__(self, name):
        print("in getitem with ", name)
        return ResponsiveAtlasView(self._atlas[name], self.cbs)
    

class ResponsiveNodeView(NodeView, ResponsiveIterable):
    def __init__(self, graph, cbs=None):
        NodeView.__init__(self, graph)
        ResponsiveIterable.__init__(self)
        self.cbs = cbs if cbs is not None else []
    
    def __iter__(self):
        return ResponsiveIterator(super().__iter__(), self.cbs)
    
    def data(self, data=True, default=None):
        if not data:
            return self
        return ResponsiveNodeDataView


class ResponsiveNodeDataView(NodeDataView, ResponsiveIterable):
    pass


class ResponsiveEdgeView(EdgeView, ResponsiveIterable):
    pass


class ResponsiveEdgeDataView(EdgeDataView, ResponsiveIterable):
    pass
