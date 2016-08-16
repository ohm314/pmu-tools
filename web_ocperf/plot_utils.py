from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.palettes import inferno

from os import path

def plot_parsed_ocperf_output(parsed_output=None, source=None):
    if parsed_output and source:
        raise Exception("Can't do streaming and static plot at the same time")

    if not parsed_output and not source:
        raise Exception("Must provide at least one data source!")


    p = figure(toolbar_sticky=False, sizing_mode="stretch_both")

    if parsed_output:
        color_idx = 0
        palette = inferno(len(parsed_output.keys()))

        for k in parsed_output.keys():
            samples = parsed_output[k]

            x = [sample[0] for sample in samples]
            y = [sample[1] for sample in samples]

            p.line(x, y, color=palette[color_idx], legend=k)

            color_idx += 1
    else:
        l = p.line(x='x', y='y', source=source)

    return p

def store_plot_at(plt, dst):
    """
    plt - plot (which)
    dst - directory (where)
    """
    script, div = components(plt, wrap_script=False)
    print("storing plot")

    with file(path.join(dst, "plot.html"), "w") as f:
        f.write(div)

    with file(path.join(dst, "script.js"), "w") as f:
        f.write(script)
