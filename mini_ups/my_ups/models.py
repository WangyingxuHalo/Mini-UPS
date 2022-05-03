from django.db import models
#from django.urls import reverse
from django.contrib.auth.models import User

# Create your models here.
class MyUser(User):
    
    def __str__(self):
        return f'{self.name}'

class Warehouse(models.Model):
    warehouseid = models.BigIntegerField(primary_key=True)
    warehousex = models.IntegerField()
    warehousey = models.IntegerField()
    
    def __str__(self):
        return f'{self.warehouseid}'

s_choices=(
        (1, "idle"),
        (2, "travelling"),
        (3, "arrived at warehouse"),
        (4, "loading"),
        (5, "delivering"),
)

class Truck(models.Model):
    id = models.AutoField(primary_key=True)
    truckid = models.IntegerField(unique=True)
    truckstatus = models.SmallIntegerField(null=False, choices=s_choices)

    def __str__(self):
        return f'{self.truckid}'

status_choices=(
        (1, "waiting for pickup"),
        (2, "waiting for loading"),
        (3, "deliverying"),
        (4, "delivered"),
)

class Package(models.Model):
    packageid = models.AutoField(primary_key=True)
    trackingnum = models.BigIntegerField()
    userid = models.IntegerField(null=True)
    destinationx = models.IntegerField(null=True)
    destinationy = models.IntegerField(null=True)
    packagestatus = models.SmallIntegerField(null=False, choices=status_choices)
    description = models.CharField(max_length=1000, null=True)
    truckid = models.IntegerField(null=True)
    warehouseid = models.IntegerField(null=True)

    def __str__(self):
        return f'{self.packageid}'

class Messages(models.Model):
    id = models.AutoField(primary_key=True)
    message_from = models.IntegerField()
    message_from_name = models.TextField()
    message_to = models.IntegerField(null=True)
    message_to_name = models.TextField()
    message = models.TextField()
    time_sent = models.DateTimeField(auto_now=True)

class Feedback(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField()
    email = models.TextField()
    content = models.TextField()