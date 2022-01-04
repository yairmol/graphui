# GraphUI
A GUI for displaying and editing graphs in a vim like editor

## Running
1. run `git submodule init` and then `git submodule update`
2. run `pip install -r requirements.txt`
3. to run the application run `main.py`

## Usage
### Editing Modes
There are several basic modes:
1. Paint Vertices mode (use `pv` shortcut) - allows to paint new vertices
2. Paint Edges (`pe` shortcut) - displays possible edges (in the selected subgraph) and allows you to paint them
3. Delete Edges (`de` shortcut) - allows to delete existing edges
4. Move Vertices (`mv` shortcut) - move the location of vertices
5. Select Vertices (`sv` shortcut) - select a subset of vertices by surrounding them

### Running commands
You can run commands in the command bar by typing `:` and then the name of the command
you want to run and its arguments (if there are any). when pressing `:` a pop up suggestion pane
will pop and help you with completions. start selecting completions using `tab` or the arrow keys 
and press enter to run the command


## Design
The architecture of the app contains three central objects
- windows
- tabs (not implemented yet)
- canvases
where windows can contain multiple tabs and tabs can contain multiple canvases

### The Canvas
The canvas is a drawing area which is composed of two main objects
- content managers
- painters

#### Content Manager
A content manager is a subclass `CanvasContentManager` and the canvas can hold several content_managers. A `CanvasContentManager` is responsible for a certain type of content drawn
on the canvas, for example there could be a `GraphContentManager` which manages drawing of a graph,
there could be `AnnotationContentManager` which manages arbitrary annotations on the canvas, a `GridContentManager` which manages the contents of a grid. A ContentManager responsibilities with respect
to it's content is respond to events such as clicking, zooming, mouse moving, etc.
A Painter is an object that paints things on a canvas in it's own way and it saves it's state
(a representation for what it drew) in the objreg. Its important to note that there can only be

#### Painter
A Painter is a class that paints on the canvas in a specific way, it responds to mouse click
and move events and paints things accordingly

### The Command and Completion Mechanism