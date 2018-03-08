import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import ScalarFormatter
import matplotlib.patches as mpatches
import pandas as pd
import warnings, matplotlib.cbook, random

warnings.filterwarnings("ignore", category=matplotlib.cbook.mplDeprecation)

"""
Instructions:

Chart is to be called from a simulation method.
*args is an array of results, info is an array of chart info
where info[0] is color char, info[1] is color, and info[2] is the label

It will chart all methods on a log or non log graph
(log is set by default) demonstrating dollar profit
and will also chart alpha.

Would like to add other chart info later, but can easily be
added.
"""

def setup():
    style.use('classic')
    plt.rcParams['figure.figsize'] = 6, 6
    plt.rcParams['figure.dpi'] = 300
    plt.grid(True)

def gen_plot(log=True, formatter="dollars"):
    ax = plt.subplot(111)

    def percent(y, pos):
        return '{:.0f}%'.format(y*100)

    def dollars(y, pos):
        return '${:,.0f}'.format(y)

    def x(y, pos):
        return '{:.2f}x'.format(y)

    if log:
        ax.set_yscale("log")

    if formatter == "percent":
        ax.yaxis.set_major_formatter(FuncFormatter(percent))
    elif formatter == "x":
        ax.yaxis.set_major_formatter(FuncFormatter(x))
    else:
        ax.yaxis.set_major_formatter(FuncFormatter(dollars))

    xfmt = matplotlib.dates.DateFormatter('%B %Y')
    ax.xaxis.set_major_formatter(xfmt)

def chart(results, info, title, log=True):
    id = random.randint(1000, 9999)
    lines = []
    key = []
    plt.figure(id, dpi=300, figsize=(10,6))
    setup()
    gen_plot(log=log)

    if title != None:
        plt.title(title)

    for i in range(len(results)):
        lines.append((results[i]['time'], results[i]['value'], info[i][0], info[i][2]))
        key.append(mpatches.Patch(color=info[i][1], label=info[i][2]))

    for line in lines:
        plt.plot(line[0], line[1], line[2], linewidth=1, label=line[3])
        plt.gcf().autofmt_xdate()

    plt.legend(loc=2,
    borderaxespad=0.,
    bbox_to_anchor=(1, 1),
    bbox_transform=plt.gcf().transFigure)

    return id;

def chart_alpha(results, info, title="Alpha"):
    id = random.randint(1000, 9999)
    lines = []
    key = []
    plt.figure(id, dpi=300, figsize=(10,6))
    setup()
    gen_plot(log=False, formatter="x")

    plt.title(title)

    for i in range(len(results)-1):
        for j in range(len(results[i]['value'])):
            results[i]['value'][j] = results[i]['value'][j] / results[len(results)-1]['value'][j]
        lines.append((results[i]['time'], results[i]['value'], info[i][0], info[i][2]))
        key.append(mpatches.Patch(color=info[i][1], label=info[i][2]))

    for line in lines:
        plt.plot(line[0], line[1], line[2], linewidth=1, label=line[3])
        plt.gcf().autofmt_xdate()

    plt.legend(loc=2,
    borderaxespad=0.,
    bbox_to_anchor=(1, 1),
    bbox_transform=plt.gcf().transFigure)

    return id;

def show(id):
    plt.figure(id, dpi=300, figsize=(10,6))
    plt.rcParams['figure.figsize'] = (10,6)
    plt.rcParams['figure.dpi'] = 300
    return plt.show()

def returns_df(report_dicts, report_titles, normalize=True):
    #Report dicts - must have both 'time' and 'value' keys
    #Report titles - must all be unique

    frames = []
    for i in range(len(report_dicts)):
        rd = report_dicts[i]
        rt = report_titles[i]
        df = pd.DataFrame(rd)
        if normalize:
            df['value'] = df['value']/df['value'][0]
        df =df.rename(columns={'value':rt})
        frames.append(df)

    result = frames[0]
    for frame in frames[1:]:
        result = result.merge(frame, on='time',how='outer')

    return result.set_index('time')

def alpha_df(df, control_col, perform_cols=None, resample='M'):
    #df - dataframe of returns with datetime index (designed for returns_df() )
    #control_col - single column name which contains the control var
    #perform_cols - list of column names for which the alpha is being calculated
    #default (None) = all columns but control_col
    #remaple - to get annual ('A'), monthly ('M') alpha.
    #Input is rule for pandas dataframe.resample() method

    df = df.copy() #don't alter original!
    if perform_cols == None:
        perform_cols = [x for x in df.columns if x != control_col]
    for p in perform_cols:
        df[p] = df[p]/df[control_col]

    return df.resample(resample).mean()
