import gtk
import os
import numpy
import datetime 
#from dreampy.utils.lmtcat_to_ephem import read_lmt_cat, source_uptimes, planetary_uptimes
#from dreampy.logging import logger
from dateutil import parser
from matplotlib.dates import  DateFormatter 
from matplotlib import cm
from matplotlib.pyplot import setp
#logger.name = __name__
from plots import MainView, BasePlotView, ChartView, ChartProperties
import matplotlib
if matplotlib.__version__ >= '1.0':
    from mpldatacursor import datacursor, HighlightingDataCursor
    MATPLOTLIBV1_0 = True
else:
    from .datacursor_pre1 import DataCursor as SimpleDataCursor
    MATPLOTLIBV1_0 = False
#from dreampy.observing.locations import location, LMT, GBT, Amherst

import IPython
if IPython.__version__ >= '0.11':
    ENABLE_GTK = True
else:
    ENABLE_GTK = False



class X64PlotBase:
    """This is the base class for dreampy plotting
    Do not use this class directly. Instead use the extended
    class X64Plot or X64PlotChart"""
    def __init__(self, **kwargs):
        self.plotobj = BasePlotView(**kwargs)
        self.alive = True
        #self.bf = bf
        try:
            gtk.set_interactive(False)
        except:
            pass
        
    def check_alive(self):
        """A simple routine that checks if the plot window is still alive
        """
        if not self.alive:
            raise Exception("Plot window has been killed, restart plot window")
        
    def add_subplot(self, nrows, ncols, plotnum, name=None, 
                    **kwargs):
        """Adds a subplot where nrows is number of rows in grid,
        and ncols is number of columns in grid, and plotnum is the
        plotnumber that always starts at 1.
        name is an optional string that you want to associate with this
        particular subplot. If name is not given, it will default to
        plotnum"""
        self.check_alive()
        return self.plotobj.add_subplot(nrows, ncols, plotnum, name,
                                        **kwargs)

    def plot(self, *args, **kwargs):
        """Plots given parameters such as data to to the current axes
        unless specified by current_axes_name='axes_name'.  If no subplot has been created a default (1,1,1) axes will be created
        NOTE: ALL AXES FUNCTIONS have latter property!!! """
        self.check_alive()
        return self.plotobj.plot(*args, **kwargs)

        
                     
    def plot_date(self, *args, **kwargs):
        self.check_alive()
        return self.plotobj.plot_date(*args, **kwargs)
    
    def hide_lines(self, lines):
        self.check_alive()
        self.plotobj.hide_lines(lines)

    def show_lines(self, lines):
        self.check_alive()
        self.plotobj.show_lines(lines)
        
    def refresh_canvas(self):
        """Clears figure, can also use L{clf} or L{clear}"""
        self.check_alive()        
        self.plotobj.refresh_canvas()

    def clf(self):
        """Clears figure, can also use L{clear} or L{refresh_canvas}"""
        self.check_alive()        
        self.refresh_canvas()

    def clear(self):
        """Clears figure, can also use L{clf} or L{refresh_canvas}"""
        self.check_alive()        
        self.refresh_canvas()

    def redraw_plot(self):
        self.check_alive()        
        self.plotobj.redraw_plot()
        
    def set_figtitle(self, title, *args, **kwargs):
        """Adds a title 'title' to the Figure. Text features
        can be added to kwargs, see matplotlib documentation on U{suptitle<http://matplotlib.sourceforge.net/api/figure_api.html?highlight=suptitle#matplotlib.figure.Figure.suptitle>}"""
        self.check_alive()        
        self.plotobj.set_figtitle(title, *args, **kwargs)

    def set_subplot_title(self, title, **kwargs):
        """Adds a title 'title' to the subplot.
        Text features can be added to kwargs, see matplotlib documentation
        on U{suptitle<http://matplotlib.sourceforge.net/api/pyplot_api.html?highlight=suptitle#matplotlib.pyplot.suptitle>}"""
        self.check_alive()        
        self.plotobj.set_subplot_title(title, **kwargs)

    def set_xlabel(self, xlabel, fontdict=None, labelpad=None, **kwargs):
        """Creates a xlabel 'xlabel'. Fondict is an optional dictionary
        which can override default text properties,
        fontdict=None sets to default properties.
        labelpad is the spacing from the xlabel to the x-axis in points. """
        self.check_alive()        
        self.plotobj.set_xlabel(xlabel, fontdict=fontdict,
                                labelpad=labelpad, **kwargs)

    def set_ylabel(self, ylabel, fontdict=None, labelpad=None, **kwargs):
        """Creates a ylabel 'ylabel'. Fondict is an optional dictionary
        which can override default text properties,
        fontdict=None sets to default properties.
        labelpad is the spacing from the ylabel to the y-axis in points. """
        self.check_alive()
        self.plotobj.set_ylabel(ylabel, fontdict=fontdict,
                                labelpad=labelpad, **kwargs)

    def annotate(self, label, xy, xytext=None, xycoords='data',
                 textcoords='data', arrowprops=None, **kwargs):
        """Annotates the point xy with text s at xytext.  If xytext is set
        to None the text appears at the point.
        arrowprops=None is the default properties set for the arrow
        which will connect the text to the data point"""
        self.check_alive()        
        self.plotobj.annotate(label, xy, xytext=xytext,
                              xycoords=xycoords, textcoords=textcoords,
                              arrowprops=arrowprops, **kwargs)

    def set_text(self, x, y, s, fontdict=None, **kwargs):
        """Adds text s at a position (x,y)
        fontdict is an optional dictionary in which you can override default
        text properties,
        fontdict=None set to default properties"""
        self.check_alive()        
        self.plotobj.set_text(x, y, s, fontdict=fontdict, **kwargs)

    def grid(self, b=None, **kwargs):
        """Adds a grid to subplot. b=None is a boolean expression,
        setting b=False for example would create the grid but not show it.
        It is assumed if b=None that the grid is to be shown"""
        self.check_alive()        
        self.plotobj.grid(b=b, **kwargs)

    def set_legend(self, *args, **kwargs):
        """Adds a legend to a subplot.  When using plot() it is useful to say
        label='label1' and so on. Adding loc=number(1-10) provides a convenient
        spot for the legend, find documentation for U{legend<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=legend#matplotlib.axes.Axes.legend>} to see number locatins"""
        self.check_alive()        
        self.plotobj.set_legend(*args, **kwargs)

    def imshow(self, X, **kwargs):
        """Displays an image X to the current axes. X may be an image,
        a two- dimensional array etc.  Everything is optional from there
        but can be useful see documentaion on matplotlib U{imshow<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=imshow#matplotlib.axes.Axes.imshow>}"""
        self.check_alive()
        return self.plotobj.imshow(X, **kwargs)

    def colorbar(self, **kwargs):
        """Displays colorbar for an image in current axis.
        current axis can also be passed using current_axes_name keyword"""
        self.check_alive()        
        self.plotobj.colorbar(**kwargs)
        
    def get_current_axis(self):
        """Returns the name of the current axis"""
        self.check_alive()
        return self.plotobj.get_current_axis()

    def hist(self,x, bins=10, range=None, normed=False,
             weights=None, cumulative=False, bottom=None,
             histtype='bar', align='mid', orientation='vertical',
             rwidth=None, log=False, **kwargs):
        """Takes a dataset x and creates a histogram of the data.
        Bins is the number of stacks the data will fit in.
        All other kwargs are optional but useful, see matplotlib
        documentation on U{hist<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=hist#matplotlib.axes.Axes.hist>}"""
        self.check_alive()
        return self.plotobj.hist(x, bins=bins, range=range,
                                 normed=normed, weights=weights,
                                 cumulative=cumulative, bottom=bottom,
                                 histtype=histtype, align=align,
                                 orientation=orientation, rwidth=rwidth,
                                 log=log, **kwargs)

    def set_axis_off(self,**kwargs):
        """Turns axis off but keeps any plots,hists etc."""
        self.check_alive()
        self.plotobj.set_axis_off()

    def set_axis_on(self,**kwargs):
        """Turns axis on if off"""
        self.check_alive()
        self.plotobj.set_axis_on()

    def set_xlim(self,xmin=None, xmax=None, emit=True, **kwargs):
        """Sets limits on x-axis. emit=True notifys observer of limit changes"""
        self.check_alive()
        self.plotobj.set_xlim(xmin=xmin, xmax=xmax, emit=emit, **kwargs)
        self.redraw_plot()
        
    def set_ylim(self,ymin=None, ymax=None, emit=True, **kwargs):
        """Sets limits on x-axis. emit=True notifys observer of limit changes"""
        self.check_alive()
        self.plotobj.set_ylim(ymin=ymin, ymax=ymax, emit=emit, **kwargs)
        self.redraw_plot()
        
    def set_xscale(self,value, **kwargs):
        """Sets xscale to something other than linear such as logarithmic.  value can be 'linear' or  'log' or  'symlog'. see matplotlib documentation on U{set_xscale<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=set_xscale#matplotlib.axes.Axes.set_xscale>} for usefull kwargs"""
        self.check_alive()
        self.plotobj.set_xscale(value, **kwargs)

    def set_yscale(self,value, **kwargs):
        """Sets yscale to something other than linear such as logarithmic.  value can be 'linear' or  'log' or  'symlog'. see matplotlib documentation on U{set_xscale<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=set_xscale#matplotlib.axes.Axes.set_xscale>} for usefull kwargs"""
        self.check_alive()        
        self.plotobj.set_yscale(value, **kwargs)

    def set_xticks(self,ticks, minor=False, **kwargs):
        """Accepts an array or list of ticks and overrides default ticks"""
        self.check_alive()
        self.plotobj.set_xticks(ticks, minor=minor)

    def set_yticks(self,ticks, minor=False, **kwargs):
        """Accepts an array or list of ticks and overrides default ticks"""
        self.check_alive()
        self.plotobj.set_yticks(ticks, minor=minor, **kwargs)

    def stem(self,x, y, linefmt='b-', markerfmt='bo', basefmt='r-', **kwargs):
        """Creates a stem plot for x and y """
        self.check_alive()
        self.plotobj.stem(x, y, linefmt=linefmt,
                          markerfmt=markerfmt, basefmt=basefmt,
                          **kwargs)

    def set_position(self, pos, which='both', **kwargs):
        """Sets the axis position with a pos list [left, bottom, width, height] in relative coordinates you would use to create a subplot"""
        self.check_alive()
        self.plotobj.set_position(pos, which=which,**kwargs)

    def set_axis_bgcolor(self, color, **kwargs):
        """Sets the current axis' background color"""
        self.check_alive()
        self.plotobj.set_axis_bgcolor(color, **kwargs)

    def semilogx(self, *args, **kwargs):
        """Sets semilog scale of x"""
        self.check_alive()
        self.plotobj.semilogx(*args, **kwargs)

    def semilogy(self, *args, **kwargs):
        """Sets semilog scale of y"""
        self.check_alive()
        self.plotobj.semilogy(*args, **kwargs)

    def scatter(self,x, y, s=20, c='b', marker='o', cmap=None,
                norm=None, vmin=None, vmax=None, alpha=1.0,
                linewidths=None, faceted=True, verts=None, **kwargs):
        """Creates a scatter plot of xdata versus ydata. s is size in points^2, c is a color, and different markers can be found in the matplotlib documentation of U{scatter<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=scatter#matplotlib.axes.Axes.scatter>} """
        self.check_alive()        
        self.plotobj.scatter(x, y, s=s, c=c, marker=marker,
                             cmap=cmap, norm=norm, vmin=vmin,
                             vmax=vmax, alpha=alpha,
                             linewidths=linewidths, faceted=faceted,
                             verts=verts, **kwargs)

    def pie(self,x, explode=None, labels=None, colors=None,
            autopct=None, pctdistance=0.6, shadow=False,
            labeldistance=1.1):
        """Creates a pie chart of an array x, the area of each wedge is x/sum(x).  See matplotlib documentation on U{pie<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=pie#matplotlib.axes.Axes.pie>} for optional parameters"""
        self.check_alive()
        self.plotobj.pie(x, explode=explode, labels=labels,
                         colors=colors, autopct=autopct,
                         pctdistance=pctdistance, shadow=sahdow,
                         labeldistance=labeldistance)
        
    def minorticks_on(self, **kwargs):
        """Creates autoscaled minor ticks to the axes"""
        self.check_alive()
        self.plotobj.minorticks_on(**kwargs)

    def minorticks_off(self, **kwargs):
        """Removes autoscaled minor ticks to the axes"""
        self.check_alive()
        self.plotobj.minorticks_off(**kwargs)

    def invert_xaxis(self,**kwargs):
        """Inverts the x-axis"""
        self.check_alive()
        self.plotobj.invert_xaxis(**kwargs)

    def invert_yaxis(self, **kwargs):
        """Inverts the y-axis"""
        self.check_alive()
        self.plotobj.invert_yaxis(**kwargs)

    def hlines(self,y, xmin, xmax, colors='k',
               linestyles='solid', label='', **kwargs):
        """Plots horizontal lines at each y from xmin to xmax """
        self.check_alive()
        self.plotobj.hlines(y, xmin, xmax, colors=colors,
                            linestyles=linestyles, label=label, **kwargs)

    def fill(self, *args, **kwargs):
        """Fills regions of x arrays and y arrays specified"""
        self.check_alive()
        self.plotobj.fill(*args, **kwargs)

    def errorbar(self, x, y, yerr=None, xerr=None, fmt='-',
                 ecolor=None, elinewidth=None, capsize=3,
                 barsabove=False, lolims=False, uplims=False,
                 xlolims=False, xuplims=False, **kwargs):
        """Plots x versus y with error deltas in yerr and xerr. Vertical errorbars are plotted if yerr is not None. Horizontal errorbars are plotted if xerr is not None.  See matplotlib documentation on U{errorbar's<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=error#matplotlib.axes.Axes.errorbar>} optional paramaters"""
        self.check_alive()
        self.plotobj.errorbar(x, y, yerr=yerr, xerr=xerr, fmt=fmt,
                              ecolor=ecolor, elinewidth=elinewidth,
                              capsize=capsize, barsabove=barsabove,
                              lolims=lolims, uplims=uplims,
                              xlolims=xlolims, xuplims=xuplims, **kwargs)

    def clear_axis(self, **kwargs):
        """Clears current or specified axis"""
        self.check_alive()
        self.plotobj.clear_axis(**kwargs)
        
    def boxplot(self, x, notch=0, sym='b+', vert=1,
                whis=1.5, positions=None, widths=None):
        """Creates a boxplot of the data in x. Notch = 0 (default) produces a rectangular box plot, notch = 1 will produce a notched box plot.  Vert=1 (default) makes a vertical boxplot vert=0 makes a horizontal boxplot.  See matplotlib documentation on U{boxplot<http://matplotlib.sourceforge.net/api/axes_api.html?highlight=boxplot#matplotlib.axes.Axes.boxplot>} for optional parameters"""
        self.check_alive()
        self.plotobj.boxplot(x, notch=notch, sym=sym, vert=vert,
                             whis=whis, positions=positions, widths=widths)

    def bar(self,left, height, width=0.8, bottom=None, color=None,
            edgecolor=None, linewidth=None, yerr=None, xerr=None,
            ecolor=None, capsize=3, align='edge',
            orientation='vertical', log=False, **kwargs):
        """Creates a bar chart of the data in x, see matplotlib documentation on bar for details on optional parameters"""
        self.check_alive()
        self.plotobj.bar(left, height, width=width, bottom=bottom,
                         color=color, edgecolor=edgecolor,
                         linewidth=linewidth, yerr=yerr, xerr=xerr,
                         ecolor=ecolor, capsize=capsize, align=align,
                         orientation=orientation, log=log, **kwargs)

    def vline(self,x=0, ymin=0, ymax=1, **kwargs):
        """Draws a vertical line at x from ymin to ymax """
        self.check_alive()
        return self.plotobj.vline(x=x, ymin=ymin, ymax=ymax, **kwargs)


    def contour(self, *args, **kwargs):
        """Contour plot of data"""
        self.check_alive()
        self.plotobj.contour(*args, **kwargs)

    def contourf(self, *args, **kwargs):
        """Filled contour plot of data"""
        self.check_alive()
        self.plotobj.contourf(*args, **kwargs)

    def get_xlims(self, **kwargs):
        return self.plotobj._get_xlims(**kwargs)

    def get_ylims(self, **kwargs):
        return self.plotobj._get_ylims(**kwargs)

    def print_figure(self, format='PNG'):
        return self.plotobj.print_figure(format=format)

    def plot_spec(self, bf, row, col, hold=False):
        self.bf = bf
        if self.bf is None:
            raise Exception("Need to pass in a BinFile instance to plot object")
        if not hasattr(self.bf, 'data_out'):
            raise Exception("BinFile instance does not have any data.")
        if not hold:
            self.clear()
            self.lines = []
        if not hasattr(self.bf, 'spec'):
            self.bf.spec = 10.*numpy.log10((numpy.abs(self.bf.data_out)**2).mean(axis=3))
        if hasattr(self.bf, 'pixel_label'):
            label="Row%d, Col%d (Pix: %s)" % (self.bf.row_start+row, self.bf.col_start+col, self.bf.pixel_label.get((row, col), 'NC'))
        else:
            label="Row%d, Col%d" % (self.bf.row_start+row, self.bf.col_start+col)
        line, = self.plot(numpy.arange(self.bf.bin_start, self.bf.bin_end+1),
                          self.bf.spec[row, col, :], linestyle='steps-mid',
                          label=label)
        self.lines.append(line)
        if MATPLOTLIBV1_0:
            HighlightingDataCursor(self.lines)
        #else:
        #    SimpleDataCursor(self.lines)
        self.set_subplot_title("%s" % self.bf.basename)
        self.set_legend(loc='best')

    def plot_all_spec(self, bf, hold=False):
        self.bf = bf
        if self.bf is None:
            raise Exception("Need to pass in a BinFile instance to plot object")
        if not hasattr(self.bf, 'data_out'):
            raise Exception("BinFile instance does not have any data.")
        if not hold:
            self.clear()
        if not hasattr(self.bf, 'spec'):
            self.bf.spec = 10.*numpy.log10((numpy.abs(self.bf.data_out)**2).mean(axis=3))
        self.lines = []
        for row in xrange(self.bf.num_rows):
            for col in xrange(self.bf.num_cols):
                if hasattr(self.bf, 'pixel_label'):
                    label="%d,%d (Pix: %s)" % (self.bf.row_start+row, self.bf.col_start+col, self.bf.pixel_label.get((row, col), 'NC'))
                else:
                    label="%d,%d" % (self.bf.row_start+row, self.bf.col_start+col)
                line, = self.plot(numpy.arange(self.bf.bin_start, self.bf.bin_end+1),
                                  self.bf.spec[row, col, :], linestyle='steps-mid',
                                  label=label)
                self.lines.append(line)
        self.set_subplot_title("%s" % self.bf.basename)
        self.set_legend(loc='best', prop={'size': 6})                
        lined = dict()
        for legline, origline in zip(self.plotobj.legend.get_lines(), self.lines):
            legline.set_picker(5)  # 5 pts tolerance
            lined[legline] = origline        
        
        # def onpick(event):
        #     # on the pick event, find the orig line corresponding to the
        #     # legend proxy line, and toggle the visibility
        #     legline = event.artist
        #     origline = lined[legline]
        #     vis = not origline.get_visible()
        #     origline.set_visible(vis)
        #     # Change the alpha on the line in the legend so we can see what lines
        #     # have been toggled
        #     if vis:
        #         legline.set_alpha(1.0)
        #     else:
        #         legline.set_alpha(0.2)
        #     self.plotobj.f.canvas.draw()
        
        # self.plotobj.f.canvas.mpl_connect('pick_event', onpick)
        if MATPLOTLIBV1_0:
            HighlightingDataCursor(self.lines)
        #else:
        #    SimpleDataCursor(self.lines)

    def implot_data(self, bf, data_type='amp',
                    vmin=None, vmax=None,
                    hold=False, title=None,
                    colorbar=True, **kwargs):
        self.bf = bf
        if self.bf is None:
            raise Exception("Need to pass in a BinFile instance to plot object")
        self.check_alive()
        if not hold:
            self.clear()
        if not hasattr(self.bf, 'cross_corr'):
            raise Exception("BinFile does not have cross correlation data. get_cross_corr_data() first on binfile")
        if not hasattr(self.bf, 'cc'):
            self.bf.cc = self.bf.cross_corr.mean(axis=2)
        if MATPLOTLIBV1_0:
            interpolation = 'none'
        else:
            interpolation = 'nearest'
        if data_type == 'amp':
            self.image = self.imshow(10*numpy.log10(numpy.abs(self.bf.cc)),
                                     cmap=cm.spectral, interpolation=interpolation,
                                     vmin=vmin, vmax=vmax,
                                     **kwargs)
        else:
            self.image = self.imshow(numpy.angle(self.bf.cc),
                                     cmap=cm.spectral, interpolation=interpolation,
                                     vmin=vmin, vmax=vmax,
                                     **kwargs)            
        ax, kw = self.plotobj._get_current_axes()
        if MATPLOTLIBV1_0:
            datacursor(self.image, display='single',bbox=dict(fc='white'),
                       arrowprops=dict(arrowstyle='simple', fc='white', alpha=0.5),
                       formatter="x: {x:.0f}\ny: {y:.0f}\nz: {z:.2f}".format)
        def format_coord(x, y):
            if data_type == 'amp':
                z = (10*numpy.log10(numpy.abs(self.bf.cc)))[x, y]
            else:
                z = (numpy.angle(self.bf.cc))[x, y]
            return 'x=%.1f, y=%.1f, z=%.2f' % (x, y, z)


        ax, kw = self.plotobj._get_current_axes()
        ax.format_coord = format_coord
        # self.set_subplot_title(title)
        if title is None:
            title = "%s" % self.bf.basename        
        self.set_subplot_title(title)
        if colorbar:
            self.colorbar()
        
    def implot_amp(self, bf, vmin=None, vmax=None,
                   hold=False, title=None,
                   colorbar=True, **kwargs):        
        self.implot_data(bf, vmin=vmin, vmax=vmax, 
                         hold=hold, title=title, 
                         colorbar=colorbar,
                         data_type='amp',
                         **kwargs)

    def implot_phase(self, bf, vmin=None, vmax=None,
                     hold=False, title=None,
                     colorbar=True, **kwargs):        
        self.implot_data(bf, vmin=vmin, vmax=vmax, 
                         hold=hold, title=title, 
                         colorbar=colorbar,
                         data_type='phase',
                         **kwargs)


    def plot_histogram(self, bf, row, col, plot_sigma=True,
                       hold=False):
        self.bf = bf
        if self.bf is None:
            raise Exception("Need to pass in a BinFile instance to plot object")
        if not hasattr(self.bf, 'data_out'):
            raise Exception("BinFile instance does not have any data.")
        if not hold:
            self.clear()
            self.lines = []
        try:
            h = self.bf.data_out[row, col, :, :].real.flatten()
        except:
            print "Error in extracting histogram"
        if hasattr(self.bf, 'pixel_label'):
            label="Row%d, Col%d (Pix: %s)" % (self.bf.row_start+row, self.bf.col_start+col, self.bf.pixel_label.get((row, col), 'NC'))
        else:
            label="Row%d, Col%d" % (self.bf.row_start+row, self.bf.col_start+col)
        self.hist(h, bins=20, label=label)
        if MATPLOTLIBV1_0:
            datacursor()
        self.set_subplot_title("%s" % self.bf.basename)
        if plot_sigma:
            y1, y2 = self.get_ylims()
            for x in (-8, 8):
                self.plot([x, x], [y1, y2], 'r--', linewidth=2, 
                          label="_nolegend_")
        self.set_xlim(-64, 64)
        self.set_legend(loc='best')
        
    def plot_receiver_row_spec(self, bf, rxrow, configfile=None,
                               hold=False):
        """
        Plots the spectral power for a receiver row.
        Assumes you have already read the config file. 
        Or you can pass the configfile in the method args
        """        
        self.bf = bf
        if self.bf is None:
            raise Exception("Need to pass in a BinFile instance to plot object")
        if configfile is None:
            if not hasattr(self.bf, 'pixeldic'):
                raise Exception("Read in config file first using read_xml_config method of BinaryFile instance")
        else:
            self.bf.read_xml_config(configfile)
        if not hasattr(self.bf, 'data_out'):
            raise Exception("BinFile instance does not have any data.")
        if not hold:
            self.clear()
        if not hasattr(self.bf, 'spec'):
            self.bf.spec = 10.*numpy.log10((numpy.abs(self.bf.data_out)**2).mean(axis=3))
        self.lines = []        
        for rxcol in range(1, 9):
            pixel = "%s,%s" % (rxrow, rxcol)
            if self.bf.pixeldic.has_key(pixel):
                row, col = self.bf.pixeldic[pixel]
                if hasattr(self.bf, 'pixel_label'):
                    label="%d,%d (Pix: %s)" % (self.bf.row_start+row, self.bf.col_start+col, self.bf.pixel_label.get((row, col), 'NC'))
                else:
                    label="%d,%d" % (self.bf.row_start+row, self.bf.col_start+col)
                line, = self.plot(numpy.arange(self.bf.bin_start, self.bf.bin_end+1),
                                  self.bf.spec[row, col, :], linestyle='steps-mid',
                                  label=label)
                self.lines.append(line)                
        self.set_subplot_title("%s" % self.bf.basename)
        self.set_legend(loc='best', prop={'size': 6})                
        if MATPLOTLIBV1_0:
            HighlightingDataCursor(self.lines)

    def plottraj(self, traj, hold=False):
        if not hold:
            self.clear()
        mint = min(traj.t)
        maxt = max(traj.t)
        self.add_subplot(4, 1, 1)
        xx = 60.0*numpy.asarray(traj.x)
        yy = 60.0*numpy.asarray(traj.y)
        self.plot(xx, yy, marker='o')
        if (min(yy) < 0):
            ymin = 1.15*min(yy)
        else:
            ymin = 0.85*min(yy)
        if (max(yy) > 0):
            ymax = 1.15*max(yy)
        else:
            ymax = 0.85*max(yy)
        self.set_ylim(ymin, ymax)
        self.set_xlabel('Position/arcmin')
        self.set_ylabel('Position/arcmin')
        self.add_subplot(4, 1, 2)
        self.plot(traj.t,traj.vx,'b',traj.t,traj.vy,
                  'g',[mint,maxt],[0.3,0.3],'r',[mint,maxt],[-0.3,-0.3],'r')
        self.set_ylim(-0.4, 0.4)
        self.set_xlabel('time/sec')
        self.set_ylabel('velocity [deg/sec]')
        self.add_subplot(4, 1, 3)
        self.plot(traj.t,traj.ax,'b',traj.t,traj.ay,'g',[mint,maxt],[0.08,0.08],'r',[mint,maxt],[-0.08,-0.08],'r')
        self.set_ylim(-0.1, 0.1)
        self.set_xlabel('time/sec')
        self.set_ylabel('acceleration [deg/sec^2]')
        self.add_subplot(4, 1, 4)
        # approximate jerk limit from Paul Ries' analysis - 0.2 arcmin/sec^3 ~ 0.003 deg/s^3
        self.plot(traj.t,traj.jx,'b',traj.t,traj.jy,'g',[mint,maxt],[0.003,0.003],'r',[mint,maxt],[-0.003,-0.003],'r')
        self.set_ylim(-0.005,0.005)
        self.set_xlabel('time/sec')
        self.set_ylabel('jerk [deg/sec^3]')
        #pyp.show()


class X64Plot(X64PlotBase, gtk.Window):
    """
    The base class for dreampy interactive plotting.
    This class provides a handy plotting tool based on
    python's matplotlib library.

    >>> from dreampy.plots import X64Plot
    >>> pl = X64Plot()
    >>> x = numpy.arange(10)
    >>> y = x**2
    >>> pl.plot(x, y, 'bo-')
    
    """
    def __init__(self, bf=None, **kwargs):
        #gobject.threads_init()
        gtk.Window.__init__(self)
        X64PlotBase.__init__(self, bf=bf, **kwargs)
        self.set_title("X64 Plot Window")
        x, y = 800, 600
        self.set_default_size(x, y)
        #self.connect("destroy", lambda x: gtk.main_quit())
        self.connect("delete_event", self.delete_event)
        #self.vbox = gtk.VBox(False, 0)
        #self.add(self.vbox)
        self.plotobj = MainView(self, **kwargs)
        self.add(self.plotobj)
        self.alive = True
        self.show_all()
        self.gtk_catchup()
        #gtk.set_interactive()
        #datacursor()

    def gtk_catchup(self):
        if ENABLE_GTK:
            from IPython.lib.inputhook import enable_gui
            enable_gui(gui='gtk')
        
    def delete_event(self, widget, event, data=None):
        #return True means will not generate destroy event next
        #print "Type Ctrl-D or exit() to exit from main terminal window"
        print "Killing plot window"
        self.alive = False
        return False
    
    def disconnect_event(self, sig):
        self.plotobj.disconnect_event(sig)

    def connect_event(self, eventname, eventfunc):
        return self.plotobj.connect_event(eventname, eventfunc)

class X64PlotChart(X64PlotBase):
    """
    A chart widget for dreampy for non-interactive plots
    """
    def __init__(self, chart_prop=None, **kwargs):
        if chart_prop is None:
            chart_prop = ChartProperties()
        chart_prop.get_properties(kwargs)
        self.plotobj = ChartView(chart_prop, **kwargs)
        self.alive = True


    def savefig(self, filename, dpi=None, facecolor='w',
                edgecolor='w', orientation='portrait',
                format='png', transparent=False, bbox_inches=None,
                pad_inches=0.1):
        """
        saves the figure into a file
        """
        print "Saving figure to file %s" % filename
        self.plotobj.savefig(filename, dpi=dpi, facecolor=facecolor,
                             edgecolor=edgecolor, orientation=orientation,
                             format=format, transparent=transparent,
                             bbox_inches=bbox_inches, pad_inches=pad_inches)
