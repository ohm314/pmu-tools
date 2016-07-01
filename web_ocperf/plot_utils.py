from bokeh.plotting import figure
from bokeh.embed import components

from os import path

def plot_parsed_ocperf_output(parsed_output):
    k = parsed_output.keys()[0]
    samples = parsed_output[k]

    x = [sample[0] for sample in samples]
    y = [sample[1] for sample in samples]

    p = figure()
    p.line(x, y)

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
