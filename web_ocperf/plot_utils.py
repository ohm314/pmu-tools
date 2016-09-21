import bokeh
from bokeh.plotting import figure
from bokeh.models import HoverTool
from bokeh.models.sources import ColumnDataSource


def plot_parsed_ocperf_output(parsed_output=None, sources=None):
    if parsed_output is not None and sources is not None:
        raise Exception("Can't do streaming and static plot at the same time")

    if parsed_output is None and sources is None:
        raise Exception("Must provide at least one data sources!")

    fig = figure(toolbar_sticky=False, plot_width=640, plot_height=480,
                 responsive=True)
    hover = HoverTool()

    color_idx = 0
    palette = bokeh.palettes.brewer['Dark2'][8]

    # static plot
    if parsed_output is not None:

        for event in parsed_output.event_name.unique():
            if event == 'cycles':
                continue # skip because this is just the sample leader
            data = parsed_output[parsed_output.event_name == event]
            src = ColumnDataSource(data=data)
            fig.line('timestamp', 'value',
                     source=src, legend=event, color=palette[color_idx])

            color_idx += 1

        if 'symbol' in list(parsed_output):
            hover.tooltips = [
                ('time', '@timestamp'),
                ('value', '@value'),
                ('event', '@event'),
                ('symbol', '@symbol'),
                ('location', '#@location'),
            ]
        else:
            hover.tooltips = [
                ('time', '@timestamp'),
                ('value', '@value'),
                ('event', '@event'),
            ]
    else:  # streaming plot
        for event, source in sources.iteritems():
            fig.line('timestamp', 'value',
                     source=source, legend=event, color=palette[color_idx])
            color_idx = (color_idx + 1) % 8
        hover.tooltips = [
            ('time', '@timestamp'),
            ('value', '@value'),
            ('event', '@event'),
        ]

    fig.add_tools(hover)
    fig.xaxis.axis_label = 'time [s]'
    fig.yaxis.axis_label = 'samples count'

    return fig
