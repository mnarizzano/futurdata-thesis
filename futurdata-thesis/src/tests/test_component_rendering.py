import tkinter as tk
import pytest
from PIL import Image
from src.main.models import ComponentBox, Diagram
from src.main.views.canvas_view import DiagramCanvas

@pytest.fixture
def canvas():
    root = tk.Tk()
    root.withdraw()
    yield DiagramCanvas(root)
    root.destroy()

@pytest.mark.parametrize("color, expected", [
    ("#000000", "white"), ("#000080", "white"), ("#006400", "white"),
    ("#800000", "white"), ("#333333", "white"), ("#400060", "white"),
    ("#ffffff", "black"), ("#ffff00", "black"), ("#dddddd", "black")])
def test_contrast(canvas, color, expected):
    shape = ComponentBox(200, 200)
    shape.properties.update(node_type="Leaf", color_id=1)
    canvas.color_resolver = lambda _: {"hex_code": color}
    canvas.draw_shape(shape)
    assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == expected

@pytest.mark.parametrize("size", [(200, 100), (100, 200)])
def test_image_layout_and_lifecycle(canvas, tmp_path, size):
    path = tmp_path / "component.png"
    Image.new("RGB", size, "red").save(path)
    shape = ComponentBox(200, 200)
    shape.text = "A long component name that needs several label lines"
    shape.properties.update(image_path=str(path), node_type="Leaf", color_id=1)
    canvas.color_resolver = lambda _: {"hex_code": "#000080"}
    diagram = Diagram()
    diagram.shapes = [shape]
    canvas.redraw_all(diagram)
    item, _, width, height, photo = canvas._component_images[shape]
    assert canvas.itemcget(canvas._canvas_items[shape]['body'], "fill") == "white"
    assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == "black"
    pixels = photo._PhotoImage__photo
    colored = [(x, y) for y in range(photo.height()) for x in range(photo.width())
               if pixels.get(x, y) == (255, 0, 0)]
    xs, ys = zip(*colored)
    ratio = (max(xs) - min(xs) + 1) / (max(ys) - min(ys) + 1)
    assert ratio == pytest.approx(size[0] / size[1], rel=.04)
    assert canvas.bbox(item)[3] <= canvas.bbox(canvas._canvas_items[shape]['text'])[1]
    assert canvas.bbox(canvas._canvas_items[shape]['text'])[3] < canvas.render_bounds(shape)[3]
    before = canvas.coords(item)
    shape.move(15, 20)
    canvas.move_items(shape, 15, 20)
    assert canvas.coords(item) == pytest.approx([before[0] + 15, before[1] + 20])
    canvas._apply_zoom(2, 0, 0)
    photo = canvas._component_images[shape][4]
    assert (photo.width(), photo.height()) == (round(width * 2), round(height * 2))
    canvas.redraw_all(diagram)
    assert sum(canvas.type(i) == "image" for i in canvas.find_all()) == 1
    shape.properties["image_path"] = ""
    canvas.draw_shape(shape)
    assert not canvas._component_images
    assert all(canvas.type(i) != "image" for i in canvas.find_all())
    assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == "white"


def test_missing_and_corrupt_image(canvas, tmp_path):
    shape = ComponentBox(200, 200)
    shape.properties.update(node_type="Leaf", color_id=1)
    canvas.color_resolver = lambda _: {"hex_code": "#000000"}
    path = tmp_path / "bad.png"
    for corrupt in (False, True):
        if corrupt:
            path.write_text("invalid image")
        shape.properties["image_path"] = str(path)
        canvas.draw_shape(shape)
        assert not canvas._component_images
        assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == "white"
        assert shape.HEIGHT == ComponentBox.HEIGHT


@pytest.mark.parametrize("background, expected", [("white", "black"), ("#222222", "white")])
def test_transparent_catalog_color_uses_canvas_background(canvas, background, expected):
    canvas.configure(background=background)
    shape = ComponentBox(200, 200)
    shape.properties.update(node_type="Leaf", color_id=1)
    canvas.color_resolver = lambda _: {"name": "Transparent", "hex_code": "#000000"}
    canvas.draw_shape(shape)
    assert canvas.itemcget(canvas._canvas_items[shape]['body'], "fill") == ""
    assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == expected
    canvas.color_resolver = lambda _: {"name": "Black", "hex_code": "#000000"}
    canvas.draw_shape(shape)
    assert canvas.itemcget(canvas._canvas_items[shape]['body'], "fill") == "#000000"
    assert canvas.itemcget(canvas._canvas_items[shape]['text'], "fill") == "white"
