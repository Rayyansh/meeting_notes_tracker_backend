from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email: str, name: str, password: str) -> "User":
        user = self.model(email=self.normalize_email_address(email), name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @staticmethod
    def normalize_email_address(email: str) -> str:
        return email.strip().lower()


class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=254, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email

    @staticmethod
    def create(email: str, name: str, password: str) -> "User":
        return User.objects.create_user(email=email, name=name, password=password)

    @staticmethod
    def get(user_id: int) -> "User":
        return User.objects.get(user_id=user_id)

    @staticmethod
    def email_exists(email: str) -> bool:
        return User.objects.filter(email=UserManager.normalize_email_address(email)).exists()
