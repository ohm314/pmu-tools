from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.palettes import inferno

from os import path

def plot_parsed_ocperf_output(parsed_output=None, source=None):
    if parsed_output is not None and source is not None:
        raise Exception("Can't do streaming and static plot at the same time")

    if parsed_output is None and source is None:
        raise Exception("Must provide at least one data source!")

    p = figure(toolbar_sticky=False, sizing_mode="stretch_both")

    if parsed_output is not None:
        color_idx = 0
        palette = inferno(len(parsed_output.keys()))

        for event in parsed_output.event_name.unique():
            d = parsed_output[ parsed_output.event_name == event ]

            p.line(d['timestamp'], d['value'],
                   color=palette[color_idx], legend=event)

            color_idx += 1
    else:
        l = p.line(x='x', y='y', source=source)

    return p
