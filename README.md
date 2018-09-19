
# coincharts


[`coincharts`](https://github.com/stnbu/coincharts) is a Django app that displays the normalized value of Ethereum (in US Dollars), vs the average of the normalized price of a "basket" of others. Price information is fetched from https://coinapi.io/ ever six hours (for now), using their REST API.

Obviously, there is much room for generalization. TBD.

A daemon that fetches and stores data locally is included.

You can see it in action here: https://unintuitive.org/pages/coincharts/

## Usage/Installation

### Installation

Install the package as you would any other python package

    pip install git+https://github.com/stnbu/coincharts.git

Requirements are _not_ handled automatically. You can install them with

```bash
pip install -r /path/to/coincharts/requirements.txt
```

### https://www.coinapi.io/ API

If you have not already, sign up for and acquire a CoinAPI.io authentication token [here](https://www.coinapi.io/pricing?apikey).


Create a file at `~/.coincharts/API_KEY` with your key.

Of course this file should be readable by the daemon but *security is up to you*. Be careful out there.

### Selection of Symbols

Create a file `~/.coincharts/config.yaml`

With contents

```yaml
history_symbols:
    - BITSTAMP_SPOT_BTC_USD
    - BITSTAMP_SPOT_XRP_USD
    - BITSTAMP_SPOT_ETH_USD
    - BITSTAMP_SPOT_LTC_USD
    - BITSTAMP_SPOT_BCH_USD
```

These symbols are specific to CoinAPI.io, but the above is a good start.

### Database changes

Prepare your database schema by running the Django migration tool.

```bash
manage.py makemigrations coincharts && python manage.py migrate
```

(Don't forget to backup your data first!)

### Run the daemon

The daemon _requires_ the presence of the `DJANGO_SETTINGS_MODULE` environment variable. Set it to the name of your site's setting's module (the same value that Django calculates/expects). Note that this is the _module's name_, not its path.

```bash
DJANGO_SETTINGS_MODULE='my_site.settings' coincharts-daemon --daemon /some/path
```

A PID file and a log file will be written to `/some/path` (syslog is used also but may not work on all platforms.) This directory need not be special in any way other than be writable by the user running `coincharts-daemon`.

You may wish to do something fancy like have the web server launch and manage this daemon, although this probably has some security implications. Contributions welcome.

### Modify your `views.py`

A good start would be:

```python
import svg_graph

def index(request):

    # this is the totally intuitive way of getting the ISO8601 formatted date for one week ago UTC
    one_week_ago = datetime.datetime.fromtimestamp(
        time.time() - 7 * 24 * 60 * 60,
        tz=pytz.UTC).strftime(date_format_template)

    symbols = config['history_symbols']
    comparison = SymbolComparison()
    for symbol in symbols:
        comparison[symbol] = SymbolInfo(symbol, since=one_week_ago)
    history_generator = comparison.normalized_history_averages()
    eth = comparison.pop('BITSTAMP_SPOT_ETH_USD')

    graph = svg_graph.LineGraph(
        title='Price history averages',
        height=580,
        width=1200,
        points_set=[
            svg_graph.Points(eth.normalized_history, color='green'),
            svg_graph.Points(history_generator, color='black'),
        ],
    )

    context = {
        'graph': graph.to_xml(),
    }
    return render(request, 'coincharts/index.html', context)
```

### Modifying your template

Something as simple as

```html
{% if graph %}
{% graph|safe %}
{% endif %}
```

should work. CSS appears in-line (which assumes HTML5), so nothing special is required with regard to CSS.

Known issues, limitations
-------------------------

* _You_ must run the daemon. You may wish to use your OS's "supervisor" or similar.
* It's not very pluggable for a "plug-in" (contributions welcome!)
* You must set `myapp.settings.TEMPLATES['APP_DIRS']=True` or work out access to the template yourself.
* I've had all kinds of problems with syslog. It would be great if it "just worked".
* Automating some install stuff would be nice.
* The daemon requires the presence of the DJANGO_SETTINGS_MODULE environment variable. There might be better ways...
