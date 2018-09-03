
from django.db import models


class Prices(models.Model):

    symbol_id = models.CharField(max_length=100)
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

    def __str__(self):
        class_name = self.__class__.__name__
        return '{}@{}'.format(
            self.time_period_end,
            self.price_close
        )

    class Meta:
        app_label = 'coincharts'
        get_latest_by = 'id'
