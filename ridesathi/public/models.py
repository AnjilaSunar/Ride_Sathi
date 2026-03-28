from django.db import models

class Bike(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    description = models.TextField()
    image = models.ImageField(upload_to='bikes/')

    def __str__(self):
        return self.name