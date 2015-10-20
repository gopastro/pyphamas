"""
Plotting widgets
"""
import gtk
try:
    gtk.set_interactive(False)
except:
    pass
import os
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvasChart
from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import rcParams
import matplotlib
import gtkunixprint
import types
import textwrap

from decimal import Decimal, getcontext

from StringIO import StringIO
from PIL import Image as PILImage

_new_tooltip_api =  (gtk.pygtk_version[1] >= 12)

if gtk.pygtk_version[1] >= 6:
    edit_img = gtk.STOCK_EDIT
else:
    edit_img = gtk.STOCK_PASTE

class NavToolBar(NavigationToolbar):
    def __init__(self, canvas, window):
        NavigationToolbar.__init__(self, canvas, window)
        self.comments = ''
        self.annotate = None
        self.page_setup=None
        self.settings = None

    def _init_toolbar(self):
        NavigationToolbar._init_toolbar(self)
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_PRINT, 22)
        tbutton = gtk.ToolButton(image, 'Print')
        self.insert(tbutton, -1)
        tbutton.connect('clicked', getattr(self, 'print_canvas'))
        if not _new_tooltip_api:
            tbutton.set_tooltip(self.tooltips, 'Print current view',
                                'Private')
        else:
            tbutton.set_tooltip_text('Print current view')
        image = gtk.Image()
        image.set_from_stock(edit_img, 22)
        tbutton = gtk.ToolButton(image, 'Comments')
        self.insert(tbutton, -1)
        if not _new_tooltip_api:
            tbutton.set_tooltip(self.tooltips, 'Insert Comment to Plot',
                                'Private')
        else:
            tbutton.set_tooltip_text('Insert Comment to Plot')
        tbutton.connect('clicked', getattr(self,'insert_comments'))
        self.show_all()

    def insert_comments(self, widget):
        #print 'Insert Comments'
        dialog = gtk.Dialog("Insert Comments", self.win, 0)
        #cancel_button = dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        ok_button = dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        ok_button.grab_default()

        hbox = gtk.HBox(False, 8)
        hbox.set_border_width(8)
        dialog.vbox.pack_start(hbox, False, False, 0)
        table = gtk.Table(1, 1)
        table.set_row_spacings(4)
        table.set_col_spacings(4)
        hbox.pack_start(table, True, True, 0)

        label = gtk.Label("Enter Comments for Plot: ")
        label.set_use_underline(True)
        table.attach(label, 0, 1, 0, 1)
        local_entry = gtk.Entry()
        local_entry.set_text(self.comments)
        table.attach(local_entry, 0, 1, 1, 2)

        dialog.show_all()
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.comments = local_entry.get_text()
            if not self.annotate:
                self.annotate = self.canvas.figure.axes[0].annotate(self.comments,
                                                                    xy=(0.8,0.95),
                                                                    xycoords='figure fraction',
                                                                    fontsize='smaller')
            else:
                self.annotate.set_text(self.comments)
            self.canvas.draw()
        dialog.destroy()

    def print_canvas(self, widget):
        """An alternate gtkunixprint method"""
        self._print_dialog = gtkunixprint.PrintUnixDialog(parent=self.win)
        self._print_dialog.set_manual_capabilities(gtkunixprint.PRINT_CAPABILITY_COPIES |
                                                   gtkunixprint.PRINT_CAPABILITY_PAGE_SET)
        response = self._print_dialog.run()
        if response in [gtk.RESPONSE_CANCEL,
                        gtk.RESPONSE_DELETE_EVENT]:
            self._print_dialog.destroy()
            self._print_dialog = None
        elif response == gtk.RESPONSE_OK:
            self._send_to_printer(self._print_dialog.get_selected_printer(),
                                  self._print_dialog.get_settings(),
                                  self._print_dialog.get_page_setup())
            self._print_dialog.destroy()
            self._print_dialog = None
        else:
            raise AssertionError("unhandled response: %d" % (response,))

    def print_ps(self):
        import tempfile
        (fd, temp_filename) = tempfile.mkstemp(suffix='.ps')
        self.canvas.figure.savefig(temp_filename, orientation='landscape',
                                   papertype='letter')
        return temp_filename

    def _send_to_printer(self, printer, settings, page_setup):
        report_filename = self.print_ps()

        job = gtkunixprint.PrintJob(report_filename, printer,
                                    settings, page_setup)
        job.set_source_file(report_filename)
        job.send(self._on_print_job_complete)
        os.unlink(report_filename)

    def _on_print_job_complete(self, job, data, error):
        if error:
            print 'Fixme, handle error:', error
        else:
            print "Printing done"

    # the following 3 from
    #http://www.mail-archive.com/matplotlib-users@lists.sourceforge.net/msg17822.html
    #to fix a bug in zoom plot
    def release(self, event):
        try: del self._pixmapBack
        except AttributeError: pass


class BasePlotView(object):
    """
    This is the base plot view for all dreampy plots
    When extended with gtk.Frame in MainView, it can be
    used for interactive plots.
    When extended with backend_agg, it can be used for non-interactive
    automated plotting routines (something that can be used in the lmtdcs
    framework for example)
    """
    def __init__(self, **kwargs):
        #Put some stuff
        self.suppress_header = kwargs.get('suppress_header', False)
        self.suppress_title = kwargs.get('suppress_title', False)
        self.suppress_legend = kwargs.get('suppress_legend', False)
        self.autoscale = True
        self.xmin = None
        self.xmax = None
        self.ymin = None
        self.ymax = None
        self.image = None
        self.hold_plot = False
        self.keyid = None
        self.filter = None
        self.labelsize = 8
        self.titlesize = 10
        self.ticklabelsize = 8
        self.ticklabelweight = 'normal'
        self.labelweight = 'bold'
        self.titleweight = 'bold'
        self.legendsize = 8
        self.legendweight = 'normal'
        self.hdrlabelsize = 9
        self.hdrlabelweight = 'normal'
        self.cur_axname = None
        #self.refresh_canvas()        

    def refresh_canvas(self):
        """Refresh canvas for new plots"""
        if self.canvas is not None:
            self.f.clear()
            self.canvas.draw()
            self.a = {}
            self.xlabel = {}
            self.ylabel = {}
            self.legend = {}
            self.title = {}
            self.cur_axname = None #current axis
            self.image = None

    def add_subplot(self, nrows, ncols, plotnum, name=None,
                    **kwargs):
        """nrows, ncols is number of rows and columns
        plotnum is plot number starting at number 1.
        name is a unique name for each subplot"""
        if name is None:
            name = plotnum
        self.a[name] = self.f.add_subplot(nrows, ncols, plotnum, **kwargs)
        self.cur_axname = name
        #return self.cur_axname
        return self.a[name]

    def _get_current_axes(self, **kwargs):
        """kwargs name is name of subplot"""
        if self.cur_axname is None:
            ax = self.add_subplot(1,1,1)
        if kwargs.has_key('current_axes_name'):
            #print 'current_axes_name'
            if kwargs['current_axes_name'] is None:
                ax = self.a[self.cur_axname]
            else:
                ax = self.a[kwargs['current_axes_name']]
            kwargs.pop('current_axes_name')
        else:
            ax = self.a[self.cur_axname]
        if kwargs.has_key('hold_plot'):
            self.hold_plot = kwargs['hold_plot']
            #print "hold_plot = %s" % self.hold_plot
            kwargs.pop('hold_plot')
        else:
            self.hold_plot = False
        return ax, kwargs
    
    def plot(self, *args, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        line = ax.plot(*args, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        return line

    def plot_date(self, *args, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        line = ax.plot_date(*args, **kwargs)
        self.redraw_plot()
        return line
    
    def hide_lines(self, lines):
        if lines:
            for line in lines:
                if type(line) == types.ListType:
                    for l in line:
                        l.set_visible(False)
            self.redraw_plot()

    def show_lines(self, lines):
        if lines:
            for line in lines:
                if type(line) == types.ListType:
                    for l in line:
                        l.set_visible(True)
            self.redraw_plot()            

    def redraw_plot(self):
        if self.hold_plot is False:
            if hasattr(self.canvas, 'show_all'):
                self.canvas.show_all()
            self.canvas.draw()

    def reset_rc(self):
        params = {'axes.labelsize': 10,
                  'text.fontsize': 10,
                  'xtick.labelsize': 8,
                  'ytick.labelsize': 8,
                  'legend.fontsize' : 8,
                  'text.usetex': True,
                  #'figure.subplot.top' : 0.8
                  }
        if self.suppress_header:
            params['figure.subplot.top'] = 0.9
        else:
            params['figure.subplot.top'] = 0.8
        matplotlib.rcParams.update(params)

    def set_figtitle(self, title, *args, **kwargs):
        """Creates title for Figure"""
        self.f.suptitle(title,*args,**kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_subplot_title(self, title, **kwargs):
        """Creates title for sub-plot"""
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_title(title,**kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def set_xlabel(self, xlabel, fontdict=None, labelpad=None, **kwargs):
        """Creates an xlabel for a subplot"""
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_xlabel(xlabel, fontdict=fontdict, labelpad=labelpad, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_ylabel(self, ylabel, fontdict=None, labelpad=None, **kwargs):
        """Creates an ylabel for a subplot"""
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_ylabel(ylabel, fontdict=fontdict, labelpad=labelpad, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def annotate(self, label, xy, xytext=None, xycoords='data', textcoords='data', arrowprops=None, **kwargs):
        """Annotates a position xy with label in a subplot"""
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.annotate(label, xy, xytext=xytext,
                    xycoords=xycoords, textcoords=textcoords,
                    arrowprops=arrowprops, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def set_text(self, x, y, s, fontdict=None, **kwargs):
        """Adds text to s to an xy position on the subplot"""
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.text(x, y, s, fontdict=fontdict, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def grid(self, b=None, **kwargs):
        """Adds a grid to subplot"""
        ax,kwargs = self._get_current_axes(**kwargs)        
        ax.grid(b=b, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def set_legend(self, *args, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        self.legend = ax.legend(*args,**kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def imshow(self, X, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        self.image = ax.imshow(X, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        return self.image

    def colorbar(self, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        if self.image:
            self.f.colorbar(self.image, ax=ax)
            #self.canvas.show_all()
            #self.canvas.draw()
            self.redraw_plot()
    
    def get_current_axis(self):
        """Returns the name of the current axis"""
        return self.cur_axname
    
    def hist(self, x, bins=10, range=None, normed=False, weights=None,
             cumulative=False, bottom=None, histtype='bar', align='mid',
             orientation='vertical', rwidth=None, log=False, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        n, bins, patches = ax.hist(x, bins=bins, range=range, normed=normed,
                                   weights=weights, cumulative=cumulative,
                                   bottom=bottom, histtype=histtype, align=align,
                                   orientation=orientation, rwidth=rwidth, log=log, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        return (n, bins, patches)

    def set_axis_off(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_axis_off()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_axis_on(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_axis_off()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_xlim(self, xmin=None, xmax=None, emit=True, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_xlim(xmin=xmin, xmax=xmax, emit=emit, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_ylim(self, ymin=None, ymax=None, emit=True, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_ylim(ymin=ymin, ymax=ymax, emit=emit, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_xscale(self, value, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_xscale(value,**kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_yscale(self, value, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_yscale(value,**kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_xticks(self, ticks, minor=False, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_xticks(ticks, minor=minor, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_yticks(self, ticks, minor=False, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_yticks(ticks, minor=minor, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def stem(self, x, y, linefmt='b-', markerfmt='bo', basefmt='r-', **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.stem(x, y, linefmt=linefmt, markerfmt=markerfmt,
                basefmt=basefmt)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_position(self, pos, which='both', **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_position(pos, which=which)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def set_axis_bgcolor(self,color,**kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.set_axis_bgcolor(color)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def semilogx(self, *args, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.semilogx(*args, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def semilogy(self, *args, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.semilogy(*args, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def scatter(self,x, y, s=20, c='b', marker='o',
                cmap=None, norm=None, vmin=None, vmax=None,
                alpha=1.0, linewidths=None, faceted=True,
                verts=None, **kwargs):
       ax,kwargs = self._get_current_axes(**kwargs)
       ax.scatter(x, y, s=s, c=c, marker=marker, cmap=cmap,
                  norm=norm, vmin=vmin, vmax=vmax, alpha=alpha,
                  linewidths=linewidths, faceted=faceted,
                  verts=verts, **kwargs)
       #self.canvas.show_all()
       #self.canvas.draw()
       self.redraw_plot()

    def pie(self,x, explode=None, labels=None, colors=None, autopct=None,
            pctdistance=0.6, shadow=False, labeldistance=1.1, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.pie(x, explode=explode, labels=labels, colors=colors,
               autopct=autopct, pctdistance=pctdistance,
               shadow=shadow, labeldistance=labeldistance, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def minorticks_on(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.minorticks_on()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def minorticks_off(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.minorticks_off()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def invert_xaxis(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.invert_xaxis()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def invert_yaxis(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.invert_yaxis()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def hlines(self, y, xmin, xmax, colors='k',
               linestyles='solid', label='', **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.hlines(y, xmin, xmax, colors=colors, linestyles=linestyles,
                  label=label, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def fill(self, *args, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.fill(*args, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def errorbar(self, x, y, yerr=None, xerr=None, fmt='-',
                 ecolor=None, elinewidth=None, capsize=3,
                 barsabove=False, lolims=False, uplims=False,
                 xlolims=False, xuplims=False, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.errorbar(x, y, yerr=yerr, xerr=xerr,
                    fmt=fmt, ecolor=ecolor, elinewidth=elinewidth,
                    capsize=capsize, barsabove=barsabove, lolims=lolims,
                    uplims=uplims, xlolims=xlolims, xuplims=xuplims, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def clear_axis(self, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.cla()
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()

    def boxplot(self, x, notch=0, sym='b+', vert=1, whis=1.5,
                positions=None, widths=None, **kwargs):
      ax,kwargs = self._get_current_axes(**kwargs)
      ax.boxplot(x, notch=notch, sym=sym, vert=vert,
                 whis=whis, positions=positions, widths=widths,
                 **kwargs)
      #self.canvas.show_all()
      #self.canvas.draw()
      self.redraw_plot()
      
    def bar(self, left, height, width=0.8, bottom=None, color=None,
            edgecolor=None, linewidth=None, yerr=None, xerr=None,
            ecolor=None, capsize=3, align='edge', orientation='vertical',
            log=False, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        ax.bar(left, height, width=width, bottom=bottom, color=color,
               edgecolor=edgecolor, linewidth=linewidth, yerr=yerr,
               xerr=xerr, ecolor=ecolor, capsize=capsize, align=align,
               orientation=orientation, log=log, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        
    def vline(self,x=0, ymin=0, ymax=1, **kwargs):
        ax,kwargs = self._get_current_axes(**kwargs)
        vline = ax.axvline(x=x, ymin=ymin, ymax=ymax, **kwargs)
        #self.canvas.show_all()
        #self.canvas.draw()
        self.redraw_plot()
        return vline
    
    def contour(self, *args, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        self.image = ax.contour(*args, **kwargs)
        self.redraw_plot()
        return self.image
    
    def contourf(self, *args, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        self.image = ax.contourf(*args, **kwargs)
        self.redraw_plot()
        return self.image
    
    def _get_ylims(self, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        return ax.get_ylim()

    def _get_xlims(self, **kwargs):
        ax, kwargs = self._get_current_axes(**kwargs)
        return ax.get_xlim()

    def print_figure(self, format='PNG'):

        self.canvas.draw()
        size = self.f.canvas.get_renderer().get_canvas_width_height()
        size = tuple(map(int, size))
        buf = self.f.canvas.tostring_rgb()
        im=PILImage.fromstring('RGB', size, buf, 'raw', 'RGB', 0, 1)
        imdata=StringIO()
        im.save(imdata, format=format)
        return imdata.getvalue()


#class MainView(gtk.Frame):
class MainView(BasePlotView, gtk.Frame):
    """
    A Gtk Frame based plotting widget for dreampy
    that contains additional tool bar items for printing
    and adding notes
    """
    def __init__(self, win, **kwargs):
        gtk.Frame.__init__(self)
        BasePlotView.__init__(self, **kwargs)
        self.win = win
        self.title = None

        #Put some stuff
        # self.suppress_header = kwargs.get('suppress_header', False)
        # self.suppress_title = kwargs.get('suppress_title', False)
        # self.suppress_legend = kwargs.get('suppress_legend', False)
        self.vbox = gtk.VBox(False, 0)
        self.add(self.vbox)
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.vbox.pack_start(self.sw, True, True, 0)
        self.sw.show()
        self.f = Figure(figsize=(5,4), dpi=100)
        self.canvas = FigureCanvas(self.f)  # a gtk.DrawingArea
        self.canvas.set_size_request(400,300)
        self.sw.add_with_viewport (self.canvas)
        self.canvas.show_all()
        self.toolbar = NavToolBar(self.canvas, self.win)
        self.vbox.pack_start(self.toolbar, False, False)
        self.toolbar.show()
        self.vbox.show()
        # self.autoscale = True
        # self.xmin = None
        # self.xmax = None
        # self.ymin = None
        # self.ymax = None
        # self.image = None
        # self.hold_plot = False
        # self.keyid = None
        # self.filter = None
        # self.labelsize = 8
        # self.titlesize = 10
        # self.ticklabelsize = 8
        # self.ticklabelweight = 'normal'
        # self.labelweight = 'bold'
        # self.titleweight = 'bold'
        # self.legendsize = 8
        # self.legendweight = 'normal'
        # self.hdrlabelsize = 9
        # self.hdrlabelweight = 'normal'
        # self.cur_axname = None
        self.refresh_canvas()
        self.show_all()
        #self.gtk_catchup()
        
    def gtk_catchup(self):
        gtk.gdk.threads_enter()
        while gtk.events_pending():
            gtk.main_iteration()
        gtk.gdk.threads_leave()        
        
    def create_arrow_button(self, arrow_type, shadow_type):
        button = gtk.Button()
        self.arrow = gtk.Arrow(arrow_type, shadow_type)
        button.add(self.arrow)
        button.show()
        self.arrow.show()
        return button

    def list_widgets_turnoff(self):
        self.left_button.set_sensitive(False)
        self.right_button.set_sensitive(False)
        self.ignore_button.set_sensitive(False)        
        #if self.keyid:
        #    self.canvas.disconnect(self.keyid)


    def disconnect_event(self, sig):
        if self.canvas:
            self.canvas.mpl_disconnect(sig)

    def connect_event(self, eventname, eventfunc):
        if self.canvas:
            self.canvas.set_flags(gtk.CAN_FOCUS)  #to grab focus for keystrokes
            self.canvas.grab_focus()    #to grab focus for keystrokes
            return self.canvas.mpl_connect(eventname, eventfunc)

    def redraw_plot(self):
        if self.hold_plot is False:
            if hasattr(self.canvas, 'show_all'):
                self.canvas.show_all()
            self.canvas.draw()
        self.gtk_catchup()

class ChartView(BasePlotView):
    """
    A non-interactive plot widget meant for printing to hard-copy
    or png images
    """
    def __init__(self, chart_prop, **kwargs):
        BasePlotView.__init__(self, **kwargs)
        self.chart_prop = chart_prop
        self.f = Figure(figsize=(self.chart_prop.size,self.chart_prop.size),
                        facecolor=self.chart_prop.facecolor)
        self.canvas = FigureCanvasChart(self.f)
        self.colors = ['blue', 'red', 'cyan', 'coral', 'blueviolet',
                       'green', 'grey', 'pink', 'magenta', 'salmon',
                       'yellow', 'chartreuse', 'darkred', 'brown']
        self.chart_colors = ['#ff0000', '#00ff00', '#0000ff',
                            '#ffff00', '#00ffff', '#ff00ff',
                            '#ff8000', '#000370', '#008080',
                            '#0088ff', '#800000', '#000080']
        self.markers = ['<' , '>' , 'D' , 'H' , '^' , 'd',
                        'h' , 'o' , 'p' , 's' , 'v' , 'x' , ',',
                        '+', '.' , '_', '1' , '2' , '3' , '4',
                        'None' , ' ' , '' ]
        #rcParams['font.family'] = 'sans-serif'
        #rcParams['font.sans-serif'] = ['Arial Condensed'] #['Helvetica Condensed']

        self.ymin = self.chart_prop.ymin
        self.ymax = self.chart_prop.ymax
        self.xmin = self.chart_prop.xmin
        self.xmax = self.chart_prop.xmax
        if self.ymin is None or self.ymax is None:
            self.ascale = True
        else:
            self.ascale = False
        getcontext().prec = 20  #pretty good precision for decimal arithmetic
        self.refresh_canvas()

    def quantize(self, flt):
        """Quantize a floating point number according to
        the self.places (based on numplaces parameter)
        using Decimal object"""
        flt_new = copy.deepcopy(flt)
        return Decimal('%f' % float(flt_new)).quantize(self.chart_prop.places)

    def _get_ylimits(self, ymin, ymax):
        print ymin, ymax, self.ymin, self.ymax
        if self.ascale:
            return (ymin, ymax)
        else:
            #use ymin and ymax provided in form input
            if self.ymin is None:
                yminimum = ymin
            else:
                yminimum = self.ymin
            if self.ymax is None:
                ymaximum = ymax
            else:
                ymaximum = self.ymax                
            return (yminimum, ymaximum)

    def scan_label(self, label, fontdict=None, **kwargs):
        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_xlim()
        x = x2+0.02*(x2-x1)
        y = y1+0.1*(y2-y1)
        #self.ax.text(2.15, -1.7, label, **kwargs)
        self.annotate(label, (x, y), 
                     transform=self.ax.transData,
                     horizontalalignment='left',
                     verticalalignment='bottom',                     
                     **kwargs)       

    # def print_figure(self, format='PNG'):

    #     self.canvas.draw()
    #     size = self.f.canvas.get_renderer().get_canvas_width_height()
    #     size = tuple(map(int, size))
    #     buf = self.f.canvas.tostring_rgb()
    #     im=PILImage.fromstring('RGB', size, buf, 'raw', 'RGB', 0, 1)
    #     imdata=StringIO()
    #     im.save(imdata, format=format)
    #     return imdata.getvalue()

    def savefig(self, filename, dpi=None, facecolor='w',
                edgecolor='w', orientation='portrait',
                format='png', transparent=False, bbox_inches=None,
                pad_inches=0.1):
        self.canvas.draw()
        self.f.savefig(filename, dpi=dpi, facecolor=facecolor,
                       edgecolor=edgecolor, orientation=orientation,
                       format=format, transparent=transparent,
                       bbox_inches=bbox_inches, pad_inches=pad_inches)


class ChartProperties:
    """A simple way to modify the chart characteristics.
    This class can be customized more later on"""
    def __init__(self, size=10, facecolor='w', ymin=None,
                 ymax=None, xmin=None, xmax=None,
                 ticklabelsize=10, labelsize=14,
                 legendsize=14, markersize=6, linewidth=1.0,
                 numplaces = 1,
                 ascale=True):
        self.size = size
        self.facecolor = facecolor
        self.ymin = ymin
        self.ymax = ymax
        self.xmin = xmin
        self.xmax = xmax
        self.ticklabelsize = ticklabelsize
        self.labelsize = labelsize
        self.legendsize = legendsize
        self.markersize = 6
        self.linewidth = linewidth
        self.numplaces = numplaces
        self.places = self._get_places(self.numplaces)
        self.ascale = ascale

    def _get_places(self, numplaces):
        return Decimal(10) ** -numplaces
    
    def _get_numplaces(self, form_data):
        try:
            self.numplaces = int(form_data.get("numplaces", 1))
        except ValueError:
            self.numplaces = 1
        self.places = self._get_places(self.numplaces)
        #for eg. if numplaces were 1, self.places = Decimal('0.1')
        #print self.numplaces, self.places

    def get_properties(self, form_data):
        """Get properties from form_data which is a dictionary of clean data
        from form"""
        for prop in ('size', 'facecolor', 'ymin', 'ymax',
                     'xmin', 'xmax', 'ticklabelsize', 'labelsize',
                     'legendsize', 'markersize', 'linewidth', 'ascale',
                     ):
            if form_data.get(prop, None) is not None:
                setattr(self, prop, form_data.get(prop, getattr(self, prop)))
        self._get_numplaces(form_data)
