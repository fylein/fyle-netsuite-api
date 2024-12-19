from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)

class User(AbstractBaseUser):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255
    )
    user_id = models.CharField(verbose_name='Fyle user id', max_length=255, unique=True)
    full_name = models.CharField(verbose_name='full name', max_length=255)
    active = models.BooleanField(default=True)
    staff = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)

    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['full_name', 'email']

    class Meta:
        db_table = 'users'


