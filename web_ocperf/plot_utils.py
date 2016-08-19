from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.palettes import inferno
from bokeh.models import HoverTool
from bokeh.models.sources import ColumnDataSource

from os import path

def plot_parsed_ocperf_output(parsed_output=None, source=None):
    if parsed_output is not None and source is not None:
        raise Exception("Can't do streaming and static plot at the same time")

    if parsed_output is None and source is None:
        raise Exception("Must provide at least one data source!")

    p = figure(toolbar_sticky=False, sizing_mode="stretch_both")

    hover = HoverTool()

    if parsed_output is not None:
        color_idx = 0
        palette = inferno(len(parsed_output.keys()))

        for event in parsed_output.event_name.unique():
            d = parsed_output[ parsed_output.event_name == event ]

            src = ColumnDataSource(data=d)
            p.line('timestamp', 'value',
                   source=src, legend=event, color=palette[color_idx])

            color_idx += 1

        if 'symbol' in list(parsed_output):
            hover.tooltips = [
                ('time', '@timestamp'),
                ('value', '@value'),
                ('symbol', '@symbol'),
                ('location', '#@location'),
            ]

    else:
        l = p.line(x='x', y='y', source=source)

    p.add_tools(hover)
    return p
