import bokeh
from bokeh.plotting import figure
from bokeh.charts import Bar
from bokeh.models.widgets import Panel, Tabs
from bokeh.models import HoverTool
from bokeh.models.sources import ColumnDataSource
from bokeh.charts.attributes import cat


def plot_by_symbol(perf_data):

    # color_idx = 0
    # palette = bokeh.palettes.brewer['Dark2'][8]

    perf_data_nocyc = perf_data[perf_data.event_name != 'cycles']
    fig = Bar(perf_data_nocyc, label=cat(columns=['symbol'], sort=False), values='value',
              group='event_name')

    fig.xaxis.axis_label = 'symbol'
    fig.yaxis.axis_label = 'samples'

    return fig


def plot_static(perf_data):
    fig_time = figure(toolbar_sticky=False, plot_width=640, plot_height=480,
                 responsive=True)
    hover = HoverTool()

    color_idx = 0
    palette = bokeh.palettes.brewer['Dark2'][8]


    for event in perf_data.event_name.unique():
        if event == 'cycles':
            continue # skip because this is just the sample leader
        data = perf_data[perf_data.event_name == event]
        src = ColumnDataSource(data=data)
        fig_time.line('timestamp', 'value',
                 source=src, legend=event, color=palette[color_idx])

        color_idx = (color_idx + 1) % 8

    if 'symbol' in list(perf_data):
        hover.tooltips = [
            ('time', '@timestamp'),
            ('value', '@value'),
            ('event', '@event'),
            ('symbol', '@symbol'),
        ]
    else:
        hover.tooltips = [
            ('time', '@timestamp'),
            ('value', '@value'),
            ('event', '@event_name'),
        ]

    fig_time.add_tools(hover)
    fig_time.xaxis.axis_label = 'time [ns]'
    fig_time.yaxis.axis_label = 'samples count'

    tab_time = Panel(child=fig_time, title="time line")

    perf_data_nocyc = perf_data[perf_data.event_name != 'cycles']
    fig_sym = Bar(perf_data_nocyc, label=cat(columns=['symbol'], sort=False),
                  values='value', group='event_name')

    fig_sym.xaxis.axis_label = 'symbol'
    fig_sym.yaxis.axis_label = 'samples'

    tab_sym = Panel(child=fig_sym, title="Symbols")

    tabs = Tabs(tabs=[tab_time, tab_sym])

    return tabs


def plot_streaming(sources):
    fig = figure(toolbar_sticky=False, plot_width=640, plot_height=480,
                 responsive=True)
    hover = HoverTool()

    color_idx = 0
    palette = bokeh.palettes.brewer['Dark2'][8]

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
    fig.xaxis.axis_label = 'time [ns]'
    fig.yaxis.axis_label = 'samples count'

    return fig
