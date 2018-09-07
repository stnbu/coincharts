
from django.db import models

# There are many datetime/price fields. We are interested almost exclusively in these two, and they are used in many places.
# Less headache if we use these ugly global names to avoid confusion 
THE_DATETIME_FIELD = 'time_period_end'
THE_PRICE_FIELD = 'price_close'

class Prices(models.Model):

    symbol = models.CharField(db_index=True, max_length=100)
    time_period_start = models.CharField(max_length=100)
    time_period_end = models.CharField(max_length=100)
    time_open = models.CharField(max_length=100)
    time_close = models.CharField(max_length=100)
    price_open = models.FloatField()
    price_high = models.FloatField()
    price_low = models.FloatField()
    price_close = models.FloatField()
    volume_traded = models.FloatField()
    trades_count = models.IntegerField()

    # Since there are multiple time/price fields, we set up aliases. The `@property` decorator seems to be
    # the cleanest way to do this.

    @property
    def price(self):
        return getattr(self, THE_PRICE_FIELD)

    @price.setter
    def price(self, value):
        setattr(self, THE_PRICE_FIELD, value)

    @property
    def dt(self):
        return getattr(self, THE_DATETIME_FIELD)

    @dt.setter
    def dt(self, value):
        setattr(self, THE_DATETIME_FIELD, value)

    def __str__(self):
        class_name = self.__class__.__name__
        return '{}@{}'.format(
            self.dt,
            self.price
        )

    class Meta:
        app_label = 'coincharts'
        get_latest_by = 'id'
