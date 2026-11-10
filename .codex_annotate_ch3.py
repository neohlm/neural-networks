import copy
import json
import pathlib
import uuid

folder = pathlib.Path("myportfolio/study unit 3 - learning models , basic applications")
source = folder / "Chapter 3 - Forward Propagation - Intro to Neural Prediction.ipynb"
target = folder / "Chapter 3 - Forward Propagation - Intro to Neural Prediction (with my comments).ipynb"
notebook = json.loads(source.read_text(encoding="utf-8"))
original_cells = notebook["cells"]

def note(cell_id: str, text: str) -> dict:
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": text.splitlines(keepends=True)}

notes_after = {
    2: note("my-understanding-siso", """### My understanding: one input, one prediction

Forward propagation is the calculation that carries an input through the network to produce a prediction. In the first example, the input is multiplied by its weight: 8.5 x 0.1 = 0.85. The weight scales the input. If the weight is negative, the output changes in the opposite direction; whether that is useful depends on the problem.

This step makes a prediction using the current weight. It does not learn the weight.
"""),
    5: note("my-understanding-miso", """### My understanding: several inputs, one prediction

Each input is multiplied by the weight in the matching position, then the contributions are added. The inputs and weights must line up, so they need the same number of values. This is a weighted sum.

A weight alone does not tell me which input has the biggest effect: I also need to consider the size and units of that input.
"""),
    7: note("my-understanding-dot-product", """### My understanding: NumPy dot product

The NumPy version uses dot product to do the same multiply-and-add calculation as the earlier loop. It should produce the same prediction when the inputs and weights are the same. The arrays also need compatible shapes.
"""),
    9: note("my-understanding-simo", """### My understanding: one input, several predictions

One input can produce several outputs by multiplying it by a separate weight for each output. Here the team's win record is used to predict more than one outcome. The result is a vector of predictions rather than one number.
"""),
    11: note("my-understanding-mimo", """### My understanding: several inputs and several predictions

Each output is its own weighted combination of the inputs. The weights are arranged so the network can calculate a different combination for each output. This lets several input features contribute to several predictions.
"""),
    13: note("my-understanding-layers", """### My understanding: passing predictions through layers

A network with more than one layer uses the first layer's values as the next layer's inputs. Forward propagation moves the values forward through these calculations until the network produces its final prediction.
"""),
    15: note("my-understanding-numpy-layers", """### My understanding: matrix multiplication for layers

NumPy expresses the layer calculations with dot products. The dimensions must match at each step: the number of values on the left side of a dot product must match the corresponding input dimension on the right.
"""),
    20: note("my-understanding-shapes", """### My understanding: element-wise multiplication and shapes

The `*` operator multiplies matching entries element by element. The `.dot()` operation combines matching values by multiplying and summing them. The array shapes determine which operation is valid, which is why some combinations raise a shape error.
"""),
}

commented = copy.deepcopy(notebook)
commented_cells = []
for index, cell in enumerate(original_cells):
    copied_cell = copy.deepcopy(cell)
    copied_cell.setdefault("id", uuid.uuid4().hex[:8])
    commented_cells.append(copied_cell)
    if index in notes_after:
        commented_cells.append(notes_after[index])

commented_cells.append(note("my-reflection", """## My reflection

The idea I understand best so far is: ______________________________

The part I want to revisit is: _____________________________________

One question I still have is: _____________________________________

These explanation notes are a starting draft. Edit them so they match my own understanding and add observations from running the notebook.
"""))
commented["cells"] = commented_cells
target.write_text(json.dumps(commented, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"Created {target}")
print(f"Original cells: {len(original_cells)}; commented-copy cells: {len(commented_cells)}")
