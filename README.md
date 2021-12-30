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
The canvas is a drawing area in which one can draw using `Painters` which 