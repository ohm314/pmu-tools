from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.palettes import inferno

from os import path

def plot_parsed_ocperf_output(parsed_output):
    color_idx = 0
    palette = inferno(len(parsed_output.keys()))

    p = figure()

    for k in parsed_output.keys():
        samples = parsed_output[k]

        x = [sample[0] for sample in samples]
        y = [sample[1] for sample in samples]

        p.line(x, y, color=palette[color_idx], legend=k)

        color_idx += 1

    return p

def store_plot_at(plt, dst):
    """
    plt - plot (which)
    dst - directory (where)
    """
    script, div = components(plt, wrap_script=False)

    with file(path.join(dst, "plot.html"), "w") as f:
        f.write(div)

    with file(path.join(dst, "script.js"), "w") as f:
        f.write(script)
